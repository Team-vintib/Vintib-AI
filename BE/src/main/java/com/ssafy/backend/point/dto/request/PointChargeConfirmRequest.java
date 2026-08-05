package com.ssafy.backend.point.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

public record PointChargeConfirmRequest(

        @Schema(description = "충전 준비(ready) 단계에서 발급받은 주문번호", example = "b1a2c3d4-e5f6-7890-abcd-ef1234567890")
        @NotBlank
        String orderId,

        @Schema(description = "결제위젯이 반환한 결제 키", example = "5EnNZRJGvaBX7zk2Ns8dv77xrx1qLm2K")
        @NotBlank
        String paymentKey,

        @Schema(description = "결제 금액(원). 준비 단계 금액과 일치해야 한다.", example = "100000")
        @Positive
        Long amount) {
}