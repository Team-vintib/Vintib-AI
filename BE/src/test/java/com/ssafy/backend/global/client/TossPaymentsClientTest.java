package com.ssafy.backend.global.client;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

/** 결제 승인 실패는 DeliveryTrackingClient와 달리 삼켜지면 안 된다 — 조용히 넘기면 포인트 미적립을 놓친다(SY035). */
class TossPaymentsClientTest {

    @Test
    void 서버에_도달할_수_없으면_결제승인실패_예외를_던진다() {
        String baseUrl = "https://127.0.0.1:1";
        RestClient restClient = RestClient.builder().baseUrl(baseUrl).build();
        TossPaymentsClient client = new TossPaymentsClient(restClient);

        assertThatThrownBy(() -> client.confirm("payment-key", "order-1", 100_000L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PAYMENT_CONFIRM_FAILED);
    }
}
