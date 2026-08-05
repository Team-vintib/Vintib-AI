package com.ssafy.backend.live.service;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.live.dto.request.LiveThumbnailUploadUrlRequest;
import com.ssafy.backend.live.dto.response.LiveThumbnailUploadUrlResponse;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 라이브 썸네일 업로드 URL 발급(FE 요청 021). {@code MemberImageService}와 같은 presigned
 * 패턴을 쓰지만, 라이브 생성 전이라 확정(confirm)할 대상이 없어 발급 한 번으로 끝난다 — 자세한
 * 이유는 {@link LiveThumbnailUploadUrlResponse}를 참고.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveThumbnailService {

    private static final Map<String, String> ALLOWED_CONTENT_TYPE_EXTENSIONS =
            Map.of("image/jpeg", "jpg", "image/png", "png", "image/webp", "webp");
    private static final String THUMBNAIL_PREFIX = "live-thumbnails/";

    private final MemberRepository memberRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    public LiveThumbnailUploadUrlResponse createUploadUrl(
            Long requesterId, Long targetId, LiveThumbnailUploadUrlRequest request) {
        requireSelf(requesterId, targetId);

        String extension = ALLOWED_CONTENT_TYPE_EXTENSIONS.get(request.contentType());
        if (extension == null) {
            throw new CustomException(ErrorCode.INVALID_IMAGE_TYPE);
        }

        String key = "%s%d/%s.%s".formatted(THUMBNAIL_PREFIX, targetId, UUID.randomUUID(), extension);
        String bucket = awsProperties.s3().publicBucket();
        S3StorageService.PresignedUpload upload =
                s3StorageService.createUploadUrl(bucket, key, request.contentType());

        return new LiveThumbnailUploadUrlResponse(
                key, upload.uploadUrl(), s3StorageService.publicUrl(bucket, key), upload.expiresInSeconds());
    }

    private void requireSelf(Long requesterId, Long targetId) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
        if (!memberRepository.existsById(targetId)) {
            throw new CustomException(ErrorCode.USER_NOT_FOUND);
        }
    }
}
