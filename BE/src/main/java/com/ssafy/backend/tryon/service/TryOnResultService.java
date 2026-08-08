package com.ssafy.backend.tryon.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.client.dto.TryOnJobRequest;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.product.service.ProductImageService;
import com.ssafy.backend.tryon.dto.response.TryOnResultResponse;
import com.ssafy.backend.tryon.entity.MemberBodyProfile;
import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.entity.TryOnResultStatus;
import com.ssafy.backend.tryon.repository.MemberBodyProfileRepository;
import com.ssafy.backend.tryon.repository.TryOnResultRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

/**
 * 시착 결과의 생성(job 접수)/조회/삭제를 다룬다. 실제 합성은 AI 워커가 비동기로 처리하므로,
 * {@link #createResult}는 job을 접수만 하고, {@link #getResult}가 아직 안 끝난 job을
 * 조회 시점에 다시 확인하는 지연 폴링으로 완료 여부를 반영한다(`docs/requests/BE/
 * 040-tryon-job-contract.md`).
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TryOnResultService {

    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");
    private static final String DEFAULT_MASK_TYPE = "upper";
    private static final String DEFAULT_FIT_TYPE = "regular";

    private final TryOnResultRepository tryOnResultRepository;
    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;
    private final MemberBodyProfileRepository memberBodyProfileRepository;
    private final ProductImageService productImageService;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;
    private final AiClient aiClient;

    /**
     * <b>쓰기 트랜잭션이어야 한다.</b> 클래스 기본({@code readOnly = true})을 그대로 쓰면
     * {@link #refreshStatus}가 건드린 엔티티 변경이 커밋 시점에 플러시되지 않고 조용히
     * 버려진다(Hibernate가 read-only 트랜잭션에서 flush mode를 MANUAL로 돌린다) — 목록을
     * 아무리 다시 불러도 완료된 job이 영원히 PENDING으로 남던 원인이었다(실측으로 발견).
     */
    @Transactional
    public List<TryOnResultResponse> getResults(Long memberId) {
        List<TryOnResult> results =
                tryOnResultRepository.findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(memberId);
        results.stream().filter(TryOnResult::isPending).forEach(this::refreshStatus);
        return results.stream()
                .map(result -> TryOnResultResponse.of(result, resultImageUrl(result)))
                .toList();
    }

    /** {@link #getResults}와 같은 이유로 쓰기 트랜잭션이어야 한다. */
    @Transactional
    public TryOnResultResponse getResult(Long memberId, Long resultId) {
        TryOnResult result = getOwnedResult(memberId, resultId);
        if (result.isPending()) {
            refreshStatus(result);
        }
        return TryOnResultResponse.of(result, resultImageUrl(result));
    }

    @Transactional
    public void deleteResult(Long memberId, Long resultId) {
        TryOnResult result = getOwnedResult(memberId, resultId);
        if (result.getImageKey() != null) {
            s3StorageService.delete(awsProperties.s3().privateBucket(), result.getImageKey());
        }
        result.softDelete();
    }

    /**
     * 시착 job을 접수한다. 회원의 시착 프로필 사진(bodyPhotoKey)이 없으면 진행할 수 없다 —
     * AI가 합성할 대상 인물 사진 자체가 없기 때문이다.
     */
    @Transactional
    public TryOnResultResponse createResult(Long memberId, Long productId) {
        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));
        MemberBodyProfile bodyProfile = memberBodyProfileRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.TRYON_PROFILE_PHOTO_REQUIRED));
        if (bodyProfile.getBodyPhotoKey() == null) {
            throw new CustomException(ErrorCode.TRYON_PROFILE_PHOTO_REQUIRED);
        }

        String userImageUrl =
                s3StorageService.presignedGetUrl(awsProperties.s3().privateBucket(), bodyProfile.getBodyPhotoKey());
        String productImageUrl = productImageService.getPrimaryImageUrls(List.of(productId)).get(productId);
        if (productImageUrl == null) {
            throw new CustomException(ErrorCode.PRODUCT_IMAGE_NOT_FOUND);
        }

        TryOnJobRequest jobRequest = new TryOnJobRequest(
                userImageUrl,
                productImageUrl,
                DEFAULT_MASK_TYPE,
                DEFAULT_FIT_TYPE,
                toDouble(bodyProfile.getHeightCm()),
                toDouble(bodyProfile.getWeightKg()),
                toDouble(bodyProfile.getWaist()),
                null);

        String jobId;
        try {
            jobId = aiClient.createTryOnJob(jobRequest);
        } catch (RestClientException e) {
            log.warn("AI 시착 job 접수 실패(memberId={}, productId={}): {}", memberId, productId, e.getMessage());
            throw new CustomException(ErrorCode.TRYON_JOB_CREATE_FAILED);
        }

        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .jobId(jobId)
                .status(TryOnResultStatus.PENDING)
                .build();
        tryOnResultRepository.save(result);

        return TryOnResultResponse.of(result, null);
    }

    @Transactional
    public TryOnResultResponse saveResult(Long memberId, Long productId, byte[] imageBytes, String contentType) {
        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(contentType);
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        String key = "tryon-results/%d/%s.%s".formatted(memberId, UUID.randomUUID(), extension);
        String bucket = awsProperties.s3().privateBucket();
        s3StorageService.put(bucket, key, imageBytes, contentType);

        TryOnResult result = TryOnResult.builder()
                .member(member)
                .product(product)
                .imageKey(key)
                .status(TryOnResultStatus.SUCCESS)
                .build();
        tryOnResultRepository.save(result);

        return TryOnResultResponse.of(result, resultImageUrl(result));
    }

    private void refreshStatus(TryOnResult result) {
        try {
            AiJobResponse job = aiClient.getJob(result.getJobId());
            if (job.isSuccess()) {
                Map<String, Object> jobResult = job.result();
                Object imageUrl = jobResult != null ? jobResult.get("image_url") : null;
                if (imageUrl == null) {
                    result.fail();
                    return;
                }
                Object fitTitle = jobResult.get("fit_title");
                Object fitDescription = jobResult.get("fit_description");
                result.complete(
                        imageUrl.toString(),
                        fitTitle != null ? fitTitle.toString() : null,
                        fitDescription != null ? fitDescription.toString() : null);
            } else if (job.isFailed()) {
                result.fail();
            } else if ("processing".equals(job.status())) {
                result.markProcessing();
            }
        } catch (RestClientException e) {
            log.warn("AI 시착 job 상태 조회 실패(resultId={}, jobId={}): {}", result.getId(), result.getJobId(), e.getMessage());
        }
    }

    // imageKey(BE S3 key, saveResult 레거시 경로)와 resultImageUrl(AI가 준 원본 URL, job 경로)
    // 중 채워진 쪽을 우선순위대로 반환한다 — 한 결과에 둘 다 채워지는 일은 없다.
    private String resultImageUrl(TryOnResult result) {
        if (result.getImageKey() != null) {
            return s3StorageService.presignedGetUrl(awsProperties.s3().privateBucket(), result.getImageKey());
        }
        return result.getResultImageUrl();
    }

    private static Double toDouble(Short value) {
        return value != null ? value.doubleValue() : null;
    }

    private TryOnResult getOwnedResult(Long memberId, Long resultId) {
        TryOnResult result = tryOnResultRepository.findById(resultId)
                .filter(r -> r.getDeletedAt() == null)
                .orElseThrow(() -> new CustomException(ErrorCode.TRYON_RESULT_NOT_FOUND));
        if (!result.isOwnedBy(memberId)) {
            throw new CustomException(ErrorCode.TRYON_RESULT_NOT_OWNER);
        }
        return result;
    }
}
