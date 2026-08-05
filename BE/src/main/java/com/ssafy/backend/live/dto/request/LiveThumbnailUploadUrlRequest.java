package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/**
 * 라이브 썸네일 업로드 URL 발급 요청(FE 요청 021). 라이브 생성 전에 올리는 사진이라
 * 프로필/커버 이미지처럼 확정(confirm) 단계를 두지 않는다 — 발급 응답에 최종 공개 URL까지
 * 함께 내려 그대로 생성 요청의 {@code thumbnailUrl}에 쓰게 한다.
 */
public record LiveThumbnailUploadUrlRequest(

        @Schema(example = "image/jpeg")
        @NotBlank
        String contentType) {
}
