package com.ssafy.backend.global.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.config.DeliveryApiConfig.DeliveryApiProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.order.entity.CourierCode;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

/** 웹훅 구독 실패는 항상 삼켜져야 한다 — deliveryapi.co.kr이 없어도 주문 흐름이 죽으면 안 된다. */
class DeliveryTrackingClientTest {

    private static final Duration TIMEOUT = Duration.ofSeconds(1);

    private DeliveryTrackingClient clientWith(String baseUrl, String apiKey, String endpointId) {
        return clientWith(baseUrl, apiKey, endpointId, "webhook-secret");
    }

    private DeliveryTrackingClient clientWith(String baseUrl, String apiKey, String endpointId, String webhookSecret) {
        DeliveryApiProperties properties =
                new DeliveryApiProperties(baseUrl, apiKey, "secret", endpointId, webhookSecret, TIMEOUT, TIMEOUT);
        RestClient restClient = RestClient.builder().baseUrl(baseUrl).build();
        return new DeliveryTrackingClient(restClient, properties);
    }

    @Test
    void 자격증명이_비어있으면_호출_없이_구독에_실패한다() {
        DeliveryTrackingClient client = clientWith("https://127.0.0.1:1", "", "");

        boolean subscribed = client.subscribe(CourierCode.CJ, "123456789012", 1L);

        assertThat(subscribed).isFalse();
    }

    @Test
    void 서버에_도달할_수_없어도_예외_없이_구독에_실패한다() {
        // 설정은 돼 있는데(자격증명·endpointId 모두 채움) 서버가 없는 상황.
        DeliveryTrackingClient client = clientWith("https://127.0.0.1:1", "key", "ep_test");

        boolean subscribed = client.subscribe(CourierCode.CJ, "123456789012", 1L);

        assertThat(subscribed).isFalse();
    }

    @Test
    void 웹훅_시크릿이_비어있으면_호출_없이_엔드포인트_등록에_실패한다() {
        DeliveryTrackingClient client = clientWith("https://127.0.0.1:1", "key", "ep_test", "");

        assertThatThrownBy(() -> client.registerEndpoint("https://example.com/webhooks/delivery", "VINTIB"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.DELIVERY_WEBHOOK_SECRET_REQUIRED);
    }

    @Test
    void 서버에_도달할_수_없으면_엔드포인트_등록에서_예외를_던진다() {
        DeliveryTrackingClient client = clientWith("https://127.0.0.1:1", "key", "ep_test");

        assertThatThrownBy(() -> client.registerEndpoint("https://example.com/webhooks/delivery", "VINTIB"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.DELIVERY_ENDPOINT_REGISTRATION_FAILED);
    }
}