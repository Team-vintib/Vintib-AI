package com.ssafy.backend.product.port.dto;

import java.time.LocalDateTime;
import lombok.Builder;

@Builder
public record LinkedLiveSummary(
    Long liveId,
    String title,
    String status,
    LocalDateTime scheduledAt,
    LocalDateTime startedAt,
    String thumbnailUrl
) {
}
