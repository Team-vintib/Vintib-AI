package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.global.client.WebhookEndpointResponse;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.service.DeliveryWebhookService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

/**
 * deliveryapi.co.kr 배송 조회 웹훅 — 수신과 엔드포인트 등록을 함께 다룬다.
 *
 * <p>{@link #receive}: 배송 상태 변경 시 deliveryapi.co.kr이 호출하는 수신 엔드포인트. JWT 인증
 * 대상이 아니다(외부 서비스가 호출) — 대신 {@code X-Webhook-Signature}로 검증한다({@code SecurityConfig}
 * PUBLIC_ENDPOINTS 참고). 엔드포인트 등록({@link #registerWebhookEndpoint}) 시 deliveryapi.co.kr이 이
 * URL로 검증용 테스트 POST를 1회 보내는데, 서명 헤더 없이 오는 경우가 있다. 헤더가 아예 없으면 서명 검증
 * 없이 200만 돌려준다(연결 확인용 ping으로 간주) — 헤더가 있는데 서명이 틀린 경우는 여전히
 * {@link DeliveryWebhookService}에서 400으로 거부한다.
 *
 * <p>{@link #registerWebhookEndpoint}: deliveryapi.co.kr에 웹훅 수신 URL({@link #receive})을
 * 등록하는 수동 트리거 전용 내부 도구. 계정당 등록 가능한 엔드포인트가 최대 10개라 앱 시작 시 자동으로
 * 부르지 않는다. 배포 환경이 바뀌어 웹훅 수신 URL을 새로 등록해야 할 때만, 개발자가 Swagger UI 등에서
 * 직접 한 번 호출한다. 일반 회원 기능이 아니라 인증만 필요하고 별도 권한 체계는 없다.
 */
@Tag(name = "주문 / 배송 / 환불(Orders)", description = "주문 생성/조회, 배송지·송장, 구매 확정, 환불 요청/승인/거절 API")
@RestController
@RequiredArgsConstructor
public class DeliveryWebhookController {

    private final DeliveryWebhookService deliveryWebhookService;
    private final DeliveryTrackingClient deliveryTrackingClient;

    @Operation(summary = "배송 상태 변경 웹훅",
            description = "deliveryapi.co.kr이 배송 상태 변경 시 호출한다. JWT 인증이 아니라 "
                    + "X-Webhook-Signature(HMAC-SHA256) 서명으로 검증한다. 서명 헤더가 없는 요청은 "
                    + "엔드포인트 등록 시의 연결 확인 ping으로 보고 그냥 200을 반환한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "처리 성공 또는 연결 확인 ping"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "서명 검증 실패 또는 잘못된 payload")
    })
    @PostMapping("/api/webhooks/delivery")
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

    @Operation(summary = "배송 조회 웹훅 엔드포인트 등록", description = "deliveryapi.co.kr에 웹훅 수신 URL을 등록하고 "
            + "endpointId를 발급받는다. 1회성 인프라 설정 — 반복 호출하면 계정당 최대 10개 한도를 소진할 수 있다. "
            + "DELIVERY_API_WEBHOOK_SECRET이 미리 설정돼 있어야 한다(비어 있으면 400).")
    @SecurityRequirement(name = "bearerAuth")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "DELIVERY_API_WEBHOOK_SECRET 미설정"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "502", description = "deliveryapi.co.kr 등록 실패")
    })
    @PostMapping("/api/internal/delivery/webhook-endpoint")
    public ResponseEntity<ApiResponse<WebhookEndpointResponse>> registerWebhookEndpoint(
            @Valid @RequestBody WebhookEndpointRegisterRequest request) {
        WebhookEndpointResponse response = deliveryTrackingClient.registerEndpoint(request.url(), request.name());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    public record WebhookEndpointRegisterRequest(
            @Schema(example = "https://i15a108.p.ssafy.io/api/webhooks/delivery") @NotBlank String url,
            @Schema(example = "VINTIB") @NotBlank String name) {
    }
}