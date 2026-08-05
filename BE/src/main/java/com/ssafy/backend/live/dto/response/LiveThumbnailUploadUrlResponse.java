package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 라이브 썸네일 업로드 URL 발급 응답(FE 요청 021).
 *
 * <p>{@code url}은 확정 전인데도 미리 내려준다 — 라이브 생성 전이라 confirm할 대상(liveId)이
 * 없어, FE가 이 값을 바로 생성 요청의 {@code thumbnailUrl}에 실어 보낸다. 실제 업로드 성공
 * 여부는 검증하지 않는다(공개 버킷의 비민감 이미지라 프로필 이미지만큼 엄격할 필요가 없다는
 * 판단 — {@code docs/plans/BE} 참고).
 */
public record LiveThumbnailUploadUrlResponse(
        @Schema(example = "live-thumbnails/1/abc123.jpg") String key,
        @Schema(example = "https://s3.example.com/live-thumbnails/1/abc123.jpg?X-Amz-...") String uploadUrl,
        @Schema(example = "https://s3.example.com/vintib-public/live-thumbnails/1/abc123.jpg") String url,
        @Schema(example = "300") long expiresInSeconds) {
}
