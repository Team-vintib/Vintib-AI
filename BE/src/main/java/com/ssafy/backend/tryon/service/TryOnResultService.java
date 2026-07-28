package com.ssafy.backend.tryon.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.tryon.dto.response.TryOnResultResponse;
import com.ssafy.backend.tryon.entity.TryOnResult;
import com.ssafy.backend.tryon.repository.TryOnResultRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 시착 결과의 저장/조회/삭제만 다룬다. 실제 AI 호출(합성 생성)은 AI 쪽 계약이
 * 확정되지 않아 이 서비스의 범위 밖이다 — {@link #saveResult}는 이미 생성된
 * 이미지를 저장하는 지점까지만 구현한다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TryOnResultService {

    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");

    private final TryOnResultRepository tryOnResultRepository;
    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public List<TryOnResultResponse> getResults(Long memberId) {
        String bucket = awsProperties.s3().privateBucket();
        return tryOnResultRepository.findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(memberId).stream()
                .map(result -> TryOnResultResponse.of(
                        result, s3StorageService.presignedGetUrl(bucket, result.getImageKey())))
                .toList();
    }

    public TryOnResultResponse getResult(Long memberId, Long resultId) {
        TryOnResult result = getOwnedResult(memberId, resultId);
        String url = s3StorageService.presignedGetUrl(awsProperties.s3().privateBucket(), result.getImageKey());
        return TryOnResultResponse.of(result, url);
    }

    @Transactional
    public void deleteResult(Long memberId, Long resultId) {
        TryOnResult result = getOwnedResult(memberId, resultId);
        s3StorageService.delete(awsProperties.s3().privateBucket(), result.getImageKey());
        result.softDelete();
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

        TryOnResult result = TryOnResult.builder().member(member).product(product).imageKey(key).build();
        tryOnResultRepository.save(result);

        return TryOnResultResponse.of(result, s3StorageService.presignedGetUrl(bucket, key));
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