package com.ssafy.backend.member.service;

import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.dto.request.MemberImageKeyRequest;
import com.ssafy.backend.member.dto.request.MemberImageUploadUrlRequest;
import com.ssafy.backend.member.dto.response.MemberImageUploadUrlResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.Map;
import java.util.UUID;
import java.util.function.BiConsumer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

/**
 * 프로필/커버 이미지 업로드(011 §5, SY030). 상품 이미지·시착 프로필 사진과 동일한 presigned
 * 2단계(발급 → 브라우저 직접 PUT → key 확인)를 쓴다. 상시 공개 노출되는 비민감 이미지라
 * {@code publicBucket}을 쓴다 — 시착 프로필의 {@code privateBucket}과는 다른 이유.
 *
 * <p>컬럼(profile_image_url/cover_image_url)엔 key가 아니라 확정 시점에 만든 최종 공개 URL을
 * 그대로 저장한다 — 응답 DTO들이 S3 의존성 없이 그대로 읽는 기존 계약을 유지하기 위해서다.
 * 그 대신 이미지를 교체·삭제할 때 컬럼에 key가 없어 이전 S3 객체는 지우지 않는다(공개 버킷의
 * 비민감 이미지라 orphan을 남겨도 실질적 문제가 없다고 판단한 트레이드오프).
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class MemberImageService {

    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");
    private static final String PROFILE_IMAGE_PREFIX = "member-profiles/";
    private static final String COVER_IMAGE_PREFIX = "member-covers/";

    private final MemberRepository memberRepository;
    private final BusinessInfoRepository businessInfoRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public MemberImageUploadUrlResponse createProfileImageUploadUrl(
            Long requesterId, Long targetId, MemberImageUploadUrlRequest request) {
        requireSelf(requesterId, targetId);
        return createUploadUrl(targetId, request, PROFILE_IMAGE_PREFIX);
    }

    public MemberImageUploadUrlResponse createCoverImageUploadUrl(
            Long requesterId, Long targetId, MemberImageUploadUrlRequest request) {
        requireSelf(requesterId, targetId);
        return createUploadUrl(targetId, request, COVER_IMAGE_PREFIX);
    }

    @Transactional
    public MemberProfileResponse confirmProfileImage(Long requesterId, Long targetId, MemberImageKeyRequest request) {
        return confirm(requesterId, targetId, request.key(), PROFILE_IMAGE_PREFIX, Member::updateProfileImage);
    }

    @Transactional
    public MemberProfileResponse confirmCoverImage(Long requesterId, Long targetId, MemberImageKeyRequest request) {
        return confirm(requesterId, targetId, request.key(), COVER_IMAGE_PREFIX, Member::updateCoverImage);
    }

    @Transactional
    public void deleteProfileImage(Long requesterId, Long targetId) {
        Member member = requireSelf(requesterId, targetId);
        member.updateProfileImage(null);
    }

    @Transactional
    public void deleteCoverImage(Long requesterId, Long targetId) {
        Member member = requireSelf(requesterId, targetId);
        member.updateCoverImage(null);
    }

    private MemberImageUploadUrlResponse createUploadUrl(
            Long memberId, MemberImageUploadUrlRequest request, String prefix) {
        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "%s%d/%s.%s".formatted(prefix, memberId, UUID.randomUUID(), extension);
        S3StorageService.PresignedUpload upload = s3StorageService.createUploadUrl(
                awsProperties.s3().publicBucket(), key, request.contentType());

        return new MemberImageUploadUrlResponse(key, upload.uploadUrl(), upload.expiresInSeconds());
    }

    private MemberProfileResponse confirm(
            Long requesterId, Long targetId, String key, String prefix, BiConsumer<Member, String> setter) {
        Member member = requireSelf(requesterId, targetId);

        String bucket = awsProperties.s3().publicBucket();
        verifyUploaded(bucket, key, prefix);
        setter.accept(member, s3StorageService.publicUrl(bucket, key));

        return MemberProfileResponse.from(member, businessVerificationStatusOf(targetId));
    }

    private Member requireSelf(Long requesterId, Long targetId) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
        return memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }

    // presigned PUT 자체는 최대 용량을 강제하지 못하므로, 확정 시점에 실제 업로드된 객체를
    // HeadObject로 검증한다(ProductImageService/TryOnProfileService.verifyUploaded와 동일 패턴).
    private void verifyUploaded(String bucket, String key, String prefix) {
        if (!key.startsWith(prefix)) {
            throw new CustomException(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
        }
        HeadObjectResponse head;
        try {
            head = s3StorageService.headObject(bucket, key);
        } catch (NoSuchKeyException e) {
            throw new CustomException(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
        }
        if (head.contentLength() != null && head.contentLength() > MAX_IMAGE_SIZE_BYTES) {
            s3StorageService.delete(bucket, key);
            throw new CustomException(ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED);
        }
    }

    // UserService.businessVerificationStatusOf와 동일 로직 — MemberProfileResponse를 채우는
    // 모든 서비스가 각자 짧게 들고 있다(BusinessInfoRepository 하나 주입해 재사용하는 수준).
    private String businessVerificationStatusOf(Long memberId) {
        return businessInfoRepository.findById(memberId)
                .map(businessInfo -> businessInfo.getVerificationStatus().name())
                .orElse("NONE");
    }
}
