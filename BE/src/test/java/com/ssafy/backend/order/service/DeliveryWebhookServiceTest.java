package com.ssafy.backend.order.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.ssafy.backend.global.config.DeliveryApiConfig.DeliveryApiProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.TrackingStatus;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import tools.jackson.databind.ObjectMapper;

@ExtendWith(MockitoExtension.class)
class DeliveryWebhookServiceTest {

    private static final String WEBHOOK_SECRET = "webhook-secret-for-test";

    @Mock
    private OrderService orderService;

    private DeliveryWebhookService deliveryWebhookService;

    @BeforeEach
    void setUp() {
        DeliveryApiProperties properties = new DeliveryApiProperties(
                "https://www.deliveryapi.co.kr", "key", "secret", "ep_test", WEBHOOK_SECRET,
                Duration.ofSeconds(1), Duration.ofSeconds(1));
        deliveryWebhookService = new DeliveryWebhookService(orderService, properties, new ObjectMapper());
    }

    private String sign(String timestamp, String rawBody) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(WEBHOOK_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] hash = mac.doFinal((timestamp + "." + rawBody).getBytes(StandardCharsets.UTF_8));
            // 문서 예시(Node.js 참조 구현)가 다이제스트 앞에 "sha256=" 접두어를 붙인다.
            return "sha256=" + HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    void 서명이_유효하면_모든_품목의_배송상태를_갱신한다() {
        String body = """
                {"event":"tracking.polled","items":[
                  {"courierCode":"cj","trackingNumber":"111","status":"DELIVERED"},
                  {"courierCode":"lotte","trackingNumber":"222","status":"IN_TRANSIT"}
                ]}""";
        String timestamp = String.valueOf(Instant.now().getEpochSecond());

        deliveryWebhookService.handle(body, timestamp, sign(timestamp, body));

        verify(orderService).updateShipmentTracking(CourierCode.CJ, "111", TrackingStatus.DELIVERED);
        verify(orderService).updateShipmentTracking(CourierCode.LOTTE, "222", TrackingStatus.IN_TRANSIT);
    }

    @Test
    void 서명이_틀리면_예외를_던지고_반영하지_않는다() {
        String body = """
                {"items":[{"courierCode":"cj","trackingNumber":"111","status":"DELIVERED"}]}""";
        String timestamp = String.valueOf(Instant.now().getEpochSecond());

        assertThatThrownBy(() -> deliveryWebhookService.handle(body, timestamp, "wrong-signature"))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_INPUT_VALUE);
        verify(orderService, never()).updateShipmentTracking(CourierCode.CJ, "111", TrackingStatus.DELIVERED);
    }

    @Test
    void 타임스탬프가_오래되면_서명이_맞아도_거부한다() {
        String body = """
                {"items":[{"courierCode":"cj","trackingNumber":"111","status":"DELIVERED"}]}""";
        String staleTimestamp = String.valueOf(Instant.now().minusSeconds(600).getEpochSecond());

        assertThatThrownBy(() -> deliveryWebhookService.handle(body, staleTimestamp, sign(staleTimestamp, body)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_INPUT_VALUE);
    }
}
