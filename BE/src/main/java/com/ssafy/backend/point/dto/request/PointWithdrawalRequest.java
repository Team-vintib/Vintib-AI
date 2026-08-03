package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Positive;

public record PointWithdrawalRequest(

        @Schema(description = "출금 신청 금액(원)", example = "50000")
        @Positive
        Long amount) {
}
