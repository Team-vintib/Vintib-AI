package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 라이브 개설 결과 응답. 예약 개설(LIVE-001)·즉시 개설(LIVE-002)이 함께 쓴다.
 */
public record LiveResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long id,

        @Schema(description = "호스트(판매자) 회원 ID", example = "1")
        Long hostId,

        @Schema(description = "방송명", example = "빈티지 데님 라이브")
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/101.jpg")
        String thumbnailUrl,

        @Schema(description = "방송 상태", example = "SCHEDULED")
        LiveStatus status,

        @Schema(description = "방송 예정 시각. 즉시 개설이면 null", example = "2026-08-01T20:00:00")
        LocalDateTime scheduledAt,

        @Schema(description = "방송 시작 시각. 예약 개설 직후에는 null", example = "2026-07-28T21:30:00")
        LocalDateTime startedAt,

        @Schema(description = "생성 시각", example = "2026-07-28T11:00:00")
        LocalDateTime createdAt
) {

    public static LiveResponse from(Live live) {
        return new LiveResponse(
                live.getId(),
                live.getHost().getId(),
                live.getTitle(),
                live.getThumbnailUrl(),
                live.getStatus(),
                live.getScheduledAt(),
                live.getStartedAt(),
                live.getCreatedAt());
    }
}