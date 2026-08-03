package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Positive;

public record PointChargeRequest(

        @Schema(description = "충전 준비 요청 금액(원). 결제위젯에 넘길 orderId를 발급받는다.", example = "100000")
        @Positive
        Long amount) {
}
