package com.ssafy.backend.tryon.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Positive;

/**
 * 전부 선택 필드다 — 값을 보내지 않은 필드는 기존에 저장된 값을 그대로 유지한다(부분 병합).
 * 온보딩에서 일부만 입력하고 라이브 시착 패널에서 나머지를 이어서 입력하는 흐름을 지원하기 위함.
 */
public record TryOnProfileUpdateRequest(

        @Schema(description = "업로드 URL 발급으로 받은 key. 사진을 바꾸지 않으면 생략", example = "tryon-profiles/1/abc123.jpg")
        String bodyPhotoKey,

        @Schema(example = "170") @Positive Short heightCm,
        @Schema(example = "60") @Positive Short weightKg,
        @Schema(example = "90") @Positive Short chest,
        @Schema(example = "70") @Positive Short waist,
        @Schema(example = "95") @Positive Short hip) {
}
