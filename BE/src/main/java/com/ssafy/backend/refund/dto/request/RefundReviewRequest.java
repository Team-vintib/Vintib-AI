package com.ssafy.backend.refund.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

public record RefundReviewRequest(

        @Schema(example = "APPROVED") @NotNull RefundDecision decision,
        @Schema(description = "REJECTED일 때 필수", example = "제품 상태를 확인했으나 하자를 확인할 수 없습니다.")
        String rejectionReason) {
}