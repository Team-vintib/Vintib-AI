package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 즉시 라이브 개설(LIVE-002) 요청.
 *
 * <p>예약과 달리 방송 시각을 받지 않는다 — 개설 즉시 시작이므로 시작 시각은 서버가 정한다.
 */
public record LiveInstantRequest(

        @Schema(description = "방송명", example = "지금 바로 여는 빈티지 라이브", maxLength = 200)
        @NotBlank
        @Size(max = 200)
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/2.jpg", maxLength = 500)
        @Size(max = 500)
        String thumbnailUrl
) {
}
