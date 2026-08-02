package com.ssafy.backend.tryon.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUpdateRequest;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUploadUrlRequest;
import com.ssafy.backend.tryon.dto.response.TryOnProfileResponse;
import com.ssafy.backend.tryon.dto.response.TryOnProfileUploadUrlResponse;
import com.ssafy.backend.tryon.entity.MemberBodyProfile;
import com.ssafy.backend.tryon.repository.MemberBodyProfileRepository;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

/**
 * AI 가상 시착 프로필(전신 사진 + 신체 치수)의 등록/조회/수정/삭제.
 *
 * <p>사진은 {@code ProductImageService}와 동일한 presigned 2단계 업로드를 쓴다 — 개인 신체
 * 사진이라 비공개 버킷에 저장하고, 조회 시마다 짧은 만료시간의 presigned GET URL을 즉석 발급한다
 * ({@link com.ssafy.backend.tryon.service.TryOnResultService}와 동일한 이유).
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TryOnProfileService {

    private static final long MAX_IMAGE_SIZE_BYTES = 10L * 1024 * 1024;
    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");

    private final MemberBodyProfileRepository memberBodyProfileRepository;
    private final MemberRepository memberRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public TryOnProfileUploadUrlResponse createUploadUrl(Long memberId, TryOnProfileUploadUrlRequest request) {
        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "tryon-profiles/%d/%s.%s".formatted(memberId, UUID.randomUUID(), extension);
        S3StorageService.PresignedUpload upload = s3StorageService.createUploadUrl(
                awsProperties.s3().privateBucket(), key, request.contentType());

        return new TryOnProfileUploadUrlResponse(key, upload.uploadUrl(), upload.expiresInSeconds());
    }

    public TryOnProfileResponse getProfile(Long memberId) {
        MemberBodyProfile profile = memberBodyProfileRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.TRYON_PROFILE_NOT_FOUND));
        return toResponse(profile);
    }

    @Transactional
    public TryOnProfileResponse upsertProfile(Long memberId, TryOnProfileUpdateRequest request) {
        MemberBodyProfile profile = memberBodyProfileRepository.findById(memberId)
                .orElseGet(() -> createProfile(memberId));

        String bucket = awsProperties.s3().privateBucket();
        String newKey = request.bodyPhotoKey();
        if (newKey != null && !newKey.equals(profile.getBodyPhotoKey())) {
            verifyUploaded(bucket, newKey);
            if (profile.getBodyPhotoKey() != null) {
                s3StorageService.delete(bucket, profile.getBodyPhotoKey());
            }
            profile.updatePhoto(newKey);
        }

        profile.mergeMeasurements(
                request.heightCm(), request.weightKg(), request.chest(), request.waist(), request.hip());

        memberBodyProfileRepository.save(profile);
        return toResponse(profile);
    }

    @Transactional
    public void deleteProfile(Long memberId) {
        MemberBodyProfile profile = memberBodyProfileRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.TRYON_PROFILE_NOT_FOUND));
        if (profile.getBodyPhotoKey() != null) {
            s3StorageService.delete(awsProperties.s3().privateBucket(), profile.getBodyPhotoKey());
        }
        memberBodyProfileRepository.delete(profile);
    }

    private MemberBodyProfile createProfile(Long memberId) {
        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        return MemberBodyProfile.builder().member(member).build();
    }

    // presigned PUT 자체는 최대 용량을 강제하지 못하므로, 등록 확인 시점에 실제 업로드된
    // 객체를 HeadObject로 검증한다(ProductImageService.verifyUploaded와 동일 패턴).
    private void verifyUploaded(String bucket, String key) {
        if (!key.startsWith("tryon-profiles/")) {
            throw new CustomException(ErrorCode.TRYON_PROFILE_UPLOAD_NOT_CONFIRMED);
        }
        HeadObjectResponse head;
        try {
            head = s3StorageService.headObject(bucket, key);
        } catch (NoSuchKeyException e) {
            throw new CustomException(ErrorCode.TRYON_PROFILE_UPLOAD_NOT_CONFIRMED);
        }
        if (head.contentLength() != null && head.contentLength() > MAX_IMAGE_SIZE_BYTES) {
            s3StorageService.delete(bucket, key);
            throw new CustomException(ErrorCode.TRYON_PROFILE_UPLOAD_NOT_CONFIRMED);
        }
    }

    private TryOnProfileResponse toResponse(MemberBodyProfile profile) {
        String bodyPhotoUrl = profile.getBodyPhotoKey() == null
                ? null
                : s3StorageService.presignedGetUrl(awsProperties.s3().privateBucket(), profile.getBodyPhotoKey());
        return new TryOnProfileResponse(
                bodyPhotoUrl,
                profile.getHeightCm(),
                profile.getWeightKg(),
                profile.getChest(),
                profile.getWaist(),
                profile.getHip(),
                profile.getUpdatedAt());
    }
}
