package com.ssafy.backend.point.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record PointChargeReadyResponse(

        @Schema(description = "결제위젯에 넘길 주문번호", example = "b1a2c3d4-e5f6-7890-abcd-ef1234567890")
        String orderId,

        @Schema(description = "충전 금액(원)", example = "100000")
        Long amount,

        @Schema(description = "결제위젯 초기화용 토스페이먼츠 클라이언트 키", example = "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq")
        String clientKey) {
}