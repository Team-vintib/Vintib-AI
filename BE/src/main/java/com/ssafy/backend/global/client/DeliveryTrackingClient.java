package com.ssafy.backend.global.client;

import com.ssafy.backend.global.config.DeliveryApiConfig.DeliveryApiProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.order.entity.CourierCode;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 택배 배송 조회 웹훅 구독(deliveryapi.co.kr).
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

    /**
     * 웹훅 수신 엔드포인트를 deliveryapi.co.kr에 등록한다(1회성 인프라 설정, 수동 트리거 전용 —
     * {@code order.controller.DeliveryWebhookController} 참고). 계정당 등록 가능한 엔드포인트가 최대 10개라
     * 반복 호출하면 한도를 소진할 수 있으므로 앱 시작 시 자동으로 부르지 않는다.
     *
     * <p>{@code webhookSecret}을 우리가 미리 정해서 함께 보낸다 — 비워서 보내면 저쪽이 임의로
     * 시크릿을 생성해 검증용 테스트 POST에 그 값으로 서명하는데, 우리는 그 값을 알 방법이 없어
     * 서명 검증이 항상 실패한다(등록 자체가 거부됨). 그래서 {@code DELIVERY_API_WEBHOOK_SECRET}이
     * 비어 있으면 호출 자체를 막는다.
     */
    public WebhookEndpointResponse registerEndpoint(String url, String name) {
        if (properties.webhookSecret().isBlank()) {
            throw new CustomException(ErrorCode.DELIVERY_WEBHOOK_SECRET_REQUIRED);
        }
        try {
            return deliveryApiRestClient.post()
                    .uri("/v1/webhooks/endpoints")
                    .body(Map.of("url", url, "name", name, "webhookSecret", properties.webhookSecret()))
                    .retrieve()
                    .body(WebhookEndpointResponse.class);
        } catch (RestClientException e) {
            log.warn("웹훅 엔드포인트 등록 실패(url={}): {}", url, e.getMessage());
            throw new CustomException(ErrorCode.DELIVERY_ENDPOINT_REGISTRATION_FAILED);
        }
    }
}