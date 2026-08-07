package com.ssafy.backend.global.delivery;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.global.client.WebhookEndpointResponse;
import com.ssafy.backend.global.response.ApiResponse;
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
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * deliveryapi.co.kr 웹훅 엔드포인트 등록 — 수동 트리거 전용 내부 도구.
 *
 * <p>계정당 등록 가능한 엔드포인트가 최대 10개라 앱 시작 시 자동으로 부르지 않는다. 배포
 * 환경이 바뀌어 웹훅 수신 URL을 새로 등록해야 할 때만, 개발자가 Swagger UI 등에서 직접
 * 한 번 호출한다. 일반 회원 기능이 아니라 인증만 필요하고 별도 권한 체계는 없다.
 */
@Tag(name = "내부 도구(Internal)", description = "배포 인프라 설정용 수동 트리거 API")
@RestController
@RequestMapping("/api/internal/delivery")
@RequiredArgsConstructor
public class DeliveryWebhookSetupController {

    private final DeliveryTrackingClient deliveryTrackingClient;

    @Operation(summary = "배송 조회 웹훅 엔드포인트 등록", description = "deliveryapi.co.kr에 웹훅 수신 URL을 등록하고 "
            + "endpointId를 발급받는다. 1회성 인프라 설정 — 반복 호출하면 계정당 최대 10개 한도를 소진할 수 있다. "
            + "DELIVERY_API_WEBHOOK_SECRET이 미리 설정돼 있어야 한다(비어 있으면 400).")
    @SecurityRequirement(name = "bearerAuth")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "DELIVERY_API_WEBHOOK_SECRET 미설정"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "502", description = "deliveryapi.co.kr 등록 실패")
    })
    @PostMapping("/webhook-endpoint")
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