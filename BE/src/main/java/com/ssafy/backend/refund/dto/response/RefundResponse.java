package com.ssafy.backend.refund.dto.response;

import com.ssafy.backend.refund.entity.RefundRequest;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record RefundResponse(
        @Schema(example = "1") Long refundId,
        @Schema(example = "10") Long orderId,
        @Schema(example = "UNDISCLOSED_DEFECT") String reason,
        @Schema(example = "소매 부분에 미고지된 얼룩이 있습니다.") String detailReason,
        @Schema(example = "REQUESTED") String status,
        @Schema(example = "null") String rejectionReason,
        @Schema(example = "2026-08-04T12:00:00") LocalDateTime requestedAt,
        @Schema(example = "null") LocalDateTime reviewedAt) {

    public static RefundResponse from(RefundRequest refund) {
        return new RefundResponse(
                refund.getId(),
                refund.getOrder().getId(),
                refund.getReason().name(),
                refund.getDetailReason(),
                refund.getStatus().name(),
                refund.getRejectionReason(),
                refund.getCreatedAt(),
                refund.getReviewedAt());
    }
}