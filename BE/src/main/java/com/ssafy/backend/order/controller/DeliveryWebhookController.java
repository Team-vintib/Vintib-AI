package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.service.DeliveryWebhookService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * deliveryapi.co.kr 배송 조회 웹훅 수신(SHIP-002). JWT 인증 대상이 아니다(외부 서비스가 호출) —
 * 대신 {@code X-Webhook-Signature}로 검증한다({@code SecurityConfig} PUBLIC_ENDPOINTS 참고).
 */
@Tag(name = "주문(Orders)", description = "배송 조회 웹훅(내부용)")
@RestController
@RequestMapping("/api/webhooks/delivery")
@RequiredArgsConstructor
public class DeliveryWebhookController {

    private final DeliveryWebhookService deliveryWebhookService;

    @Operation(summary = "배송 상태 변경 웹훅(SHIP-002)",
            description = "deliveryapi.co.kr이 배송 상태 변경 시 호출한다. JWT 인증이 아니라 "
                    + "X-Webhook-Signature(HMAC-SHA256) 서명으로 검증한다. FE/앱에서 직접 호출하지 않는다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "처리 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "서명 검증 실패 또는 잘못된 payload")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<Void>> receive(
            @RequestHeader("X-Webhook-Timestamp") String timestamp,
            @RequestHeader("X-Webhook-Signature") String signature,
            @RequestBody String rawBody) {
        deliveryWebhookService.handle(rawBody, timestamp, signature);
        return ResponseEntity.ok(ApiResponse.<Void>success(null));
    }
}
