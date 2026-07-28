package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.LocalDateTime;

/**
 * 예약 라이브 개설(LIVE-001) 요청.
 *
 * <p>방송 예정 시각은 미래여야 한다. 요청 검증 단계에서 {@code @Future}로 거르므로
 * 서비스는 "과거 시각으로 예약된 방"을 만나지 않는다.
 */
public record LiveScheduleRequest(

        @Schema(description = "방송명", example = "빈티지 데님 라이브", maxLength = 200)
        @NotBlank
        @Size(max = 200)
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/1.jpg", maxLength = 500)
        @Size(max = 500)
        String thumbnailUrl,

        @Schema(description = "방송 예정 시각. 반드시 미래여야 한다", example = "2026-08-01T20:00:00")
        @NotNull
        @Future
        LocalDateTime scheduledAt
) {
}