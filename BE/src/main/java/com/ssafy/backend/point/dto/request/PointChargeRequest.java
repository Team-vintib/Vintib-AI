package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Positive;

public record PointChargeRequest(

        @Schema(description = "충전 금액(원). 결제 연동 없이 금액만 반영하는 테스트/데모 전용 API다.", example = "100000")
        @Positive
        Long amount) {
}
