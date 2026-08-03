package com.ssafy.backend.member.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/**
 * 프로필/커버 이미지 업로드 URL 발급 요청(011 §5). 상품 이미지·시착 프로필 사진과 동일한
 * presigned 2단계 업로드의 1단계다.
 */
public record MemberImageUploadUrlRequest(

        @Schema(example = "image/jpeg")
        @NotBlank
        String contentType) {
}
