package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;

public record PointWithdrawalRequest(

        @Schema(description = "출금 신청 금액(원). 최소 10,000원.", example = "50000")
        @Min(10_000)
        Long amount) {
}