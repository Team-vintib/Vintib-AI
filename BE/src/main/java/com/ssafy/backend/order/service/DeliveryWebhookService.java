package com.ssafy.backend.order.service;

import com.ssafy.backend.global.config.DeliveryApiConfig.DeliveryApiProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.order.entity.CourierCode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * 배송 조회 웹훅 수신 처리(SHIP-002, deliveryapi.co.kr). 서명 검증 + payload 파싱만 담당하고,
 * 실제 상태 반영은 {@link OrderService#markShipmentDelivered}에 위임한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeliveryWebhookService {

    /** 문서 기준 5분 — 이보다 오래된(또는 미래) 타임스탬프는 재전송 공격으로 간주해 거부한다. */
    private static final long TIMESTAMP_TOLERANCE_SECONDS = 300;

    private final OrderService orderService;
    private final DeliveryApiProperties properties;
    private final ObjectMapper objectMapper;

    public void handle(String rawBody, String timestamp, String signature) {
        if (!isValidSignature(rawBody, timestamp, signature)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        JsonNode root;
        try {
            root = objectMapper.readTree(rawBody);
        } catch (Exception e) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        for (JsonNode item : root.path("items")) {
            if (!item.path("isDelivered").asBoolean(false)) {
                continue;
            }
            CourierCode courier = CourierCode.fromApiCode(item.path("courierCode").asText(null));
            String trackingNumber = item.path("trackingNumber").asText(null);
            if (courier == null || trackingNumber == null) {
                log.warn("배송완료 웹훅 payload에 courierCode/trackingNumber가 없다: {}", item);
                continue;
            }
            orderService.markShipmentDelivered(courier, trackingNumber);
        }
    }

    private boolean isValidSignature(String rawBody, String timestamp, String signature) {
        if (properties.webhookSecret().isBlank() || timestamp == null || signature == null) {
            return false;
        }
        try {
            long requestEpochSeconds = Long.parseLong(timestamp);
            if (Math.abs(Instant.now().getEpochSecond() - requestEpochSeconds) > TIMESTAMP_TOLERANCE_SECONDS) {
                return false;
            }

            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    properties.webhookSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] hash = mac.doFinal((timestamp + "." + rawBody).getBytes(StandardCharsets.UTF_8));
            String computed = HexFormat.of().formatHex(hash);

            return MessageDigest.isEqual(
                    computed.getBytes(StandardCharsets.UTF_8), signature.getBytes(StandardCharsets.UTF_8));
        } catch (NumberFormatException | java.security.GeneralSecurityException e) {
            return false;
        }
    }
}
