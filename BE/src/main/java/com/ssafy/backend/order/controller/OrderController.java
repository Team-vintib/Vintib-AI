package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.dto.request.OrderCreateRequest;
import com.ssafy.backend.order.dto.request.OrderShipmentAddressRequest;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.dto.response.OrderShipmentResponse;
import com.ssafy.backend.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 주문 리소스(/api/orders). 경로에 userId가 없어 requireSelf 패턴 대신 서비스 내부
// Order.isPartyOf(principal)/isBuyer에 권한 확인을 위임한다(InvoiceController와 동일한 이유).
@Tag(name = "주문(Orders)", description = "주문 생성/조회, 배송지 API")
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @Operation(summary = "상시 판매 즉시구매(SALE-002)",
            description = "상시 판매(ON_SALE) 상품을 즉시 구매한다. 결제는 포인트로만 처리되며, "
                    + "결제 금액은 즉시 tradeEscrow(거래 대금 보관)로 옮겨진다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "주문 생성 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잔액 부족, 구매 불가 상품, 자기 상품 구매 등"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 상품")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<OrderListItemResponse>> createOrder(
            Authentication authentication, @Valid @RequestBody OrderCreateRequest request) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.createOrder(memberId, request)));
    }

    @Operation(summary = "주문 상세 조회",
            description = "주문 1건을 상세 조회한다(MY-003). 해당 주문의 구매자/판매자만 조회할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{orderId}")
    public ResponseEntity<ApiResponse<OrderListItemResponse>> getOrderDetail(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.getOrderDetail(orderId, memberId)));
    }

    @Operation(summary = "주문 배송지 등록/수정(ORDER-001)",
            description = "구매자가 배송지를 등록/수정한다. 판매자가 송장을 등록(SHIP-001)하기 전(PAID 상태)까지만 가능하다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록/수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "이미 송장이 등록된 주문(PAID 아님)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "구매자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{orderId}/address")
    public ResponseEntity<ApiResponse<OrderShipmentResponse>> registerAddress(
            Authentication authentication, @PathVariable Long orderId,
            @Valid @RequestBody OrderShipmentAddressRequest request) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.registerAddress(orderId, memberId, request)));
    }

    @Operation(summary = "주문 배송지 조회(ORDER-001)",
            description = "구매자·판매자 모두 조회할 수 있다. 아직 등록 전이면 404.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문 또는 미등록 배송지")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{orderId}/address")
    public ResponseEntity<ApiResponse<OrderShipmentResponse>> getAddress(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.getShipment(orderId, memberId)));
    }
}
