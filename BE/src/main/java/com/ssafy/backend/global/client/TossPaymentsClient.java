package com.ssafy.backend.global.client;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 토스페이먼츠 결제위젯 승인 연동(POINT-001).
 *
 * <p>{@code DeliveryTrackingClient}와 달리 실패를 삼키지 않는다 — 결제 승인 실패를 조용히
 * 넘기면 포인트가 적립되지 않았는데도 성공으로 보이는 사고로 이어질 수 있어, 예외로 그대로
 * 전파해 호출자(PointService)가 충전 상태를 FAILED로 남기게 한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TossPaymentsClient {

    private final RestClient tossPaymentsRestClient;

    public TossPaymentConfirmResponse confirm(String paymentKey, String orderId, Long amount) {
        try {
            return tossPaymentsRestClient.post()
                    .uri("/v1/payments/confirm")
                    .body(Map.of("paymentKey", paymentKey, "orderId", orderId, "amount", amount))
                    .retrieve()
                    .body(TossPaymentConfirmResponse.class);
        } catch (RestClientException e) {
            log.warn("토스페이먼츠 결제 승인 실패(orderId={}): {}", orderId, e.getMessage());
            throw new CustomException(ErrorCode.PAYMENT_CONFIRM_FAILED);
        }
    }
}
