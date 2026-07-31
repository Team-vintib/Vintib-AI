package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.port.dto.LinkedLiveSummary;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record LinkedLiveSummaryResponse(
    @Schema(example = "10") Long liveId,
    @Schema(example = "빈티지 리바이스 특가전") String title,
    @Schema(example = "SCHEDULED") String status,
    @Schema(example = "2026-07-29T12:00:00") LocalDateTime scheduledAt,
    @Schema(example = "2026-07-29T12:00:00") LocalDateTime startedAt,
    @Schema(example = "https://example.com/thumbnail.jpg") String thumbnailUrl
) {
    public static LinkedLiveSummaryResponse from(LinkedLiveSummary summary) {
        if (summary == null) {
            return null;
        }
        return new LinkedLiveSummaryResponse(
            summary.liveId(),
            summary.title(),
            summary.status(),
            summary.scheduledAt(),
            summary.startedAt(),
            summary.thumbnailUrl()
        );
    }
}
