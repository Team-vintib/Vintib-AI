package com.ssafy.backend.global.client;

import com.ssafy.backend.global.config.DeliveryApiConfig.DeliveryApiProperties;
import com.ssafy.backend.order.entity.CourierCode;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 택배 배송 조회 웹훅 구독(deliveryapi.co.kr, SHIP-001/002).
 *
 * <p>자격증명이 없거나(로컬/CI) 호출이 실패하면(무료 티어 소진, 네트워크 오류 등) 예외를 삼키고
 * {@code false}를 반환한다 — {@code AiClient#isHealthy}와 같은 방어. 호출자(OrderService)가 이
 * 신호로 즉시-확정 폴백 여부를 결정한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DeliveryTrackingClient {

    private final RestClient deliveryApiRestClient;
    private final DeliveryApiProperties properties;

    /** 주문 1건의 배송 상태 변화를 웹훅으로 받도록 구독한다. 등록 성공 시에만 true. */
    public boolean subscribe(CourierCode courierCode, String trackingNumber, Long orderId) {
        if (!properties.isConfigured()) {
            return false;
        }

        try {
            deliveryApiRestClient.post()
                    .uri("/v1/webhooks/register")
                    .body(Map.of(
                            "items", List.of(Map.of(
                                    "courierCode", courierCode.getApiCode(),
                                    "trackingNumber", trackingNumber,
                                    "clientId", "order-" + orderId)),
                            "endpointId", properties.endpointId(),
                            "recurring", true,
                            "metadata", Map.of("orderId", orderId)))
                    .retrieve()
                    .toBodilessEntity();
            return true;
        } catch (RestClientException e) {
            log.warn("택배 배송 조회 웹훅 구독 실패(orderId={}): {}", orderId, e.getMessage());
            return false;
        }
    }
}
