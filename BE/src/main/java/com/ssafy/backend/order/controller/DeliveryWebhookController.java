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
 *
 * <p>엔드포인트 등록({@code POST /v1/webhooks/endpoints}) 시 deliveryapi.co.kr이 이 URL로
 * 검증용 테스트 POST를 1회 보내는데, 서명 헤더 없이 오는 경우가 있다. 헤더가 아예 없으면
 * 서명 검증 없이 200만 돌려준다(연결 확인용 ping으로 간주) — 헤더가 있는데 서명이 틀린 경우는
 * 여전히 {@link DeliveryWebhookService}에서 400으로 거부한다.
 */
@Tag(name = "주문 / 배송 / 환불(Orders)", description = "주문 생성/조회, 배송지·송장, 구매 확정, 환불 요청/승인/거절 API")
@RestController
@RequestMapping("/api/webhooks/delivery")
@RequiredArgsConstructor
public class DeliveryWebhookController {

    private final DeliveryWebhookService deliveryWebhookService;

    @Operation(summary = "배송 상태 변경 웹훅",
            description = "deliveryapi.co.kr이 배송 상태 변경 시 호출한다. JWT 인증이 아니라 "
                    + "X-Webhook-Signature(HMAC-SHA256) 서명으로 검증한다. 서명 헤더가 없는 요청은 "
                    + "엔드포인트 등록 시의 연결 확인 ping으로 보고 그냥 200을 반환한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "처리 성공 또는 연결 확인 ping"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "서명 검증 실패 또는 잘못된 payload")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<Void>> receive(
            @RequestHeader(value = "X-Webhook-Timestamp", required = false) String timestamp,
            @RequestHeader(value = "X-Webhook-Signature", required = false) String signature,
            @RequestBody(required = false) String rawBody) {
        if (timestamp == null && signature == null) {
            return ResponseEntity.ok(ApiResponse.<Void>success(null));
        }
        deliveryWebhookService.handle(rawBody, timestamp, signature);
        return ResponseEntity.ok(ApiResponse.<Void>success(null));
    }
}