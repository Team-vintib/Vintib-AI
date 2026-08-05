package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.dto.request.OrderCreateRequest;
import com.ssafy.backend.order.dto.request.OrderShipmentAddressRequest;
import com.ssafy.backend.order.dto.request.OrderShipmentRegisterRequest;
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
// Order.isPartyOf(principal)/isBuyer/isSeller에 권한 확인을 위임한다(InvoiceController와 동일한 이유).
@Tag(name = "주문 / 배송 / 환불(Orders)", description = "주문 생성/조회, 배송지·송장, 구매 확정, 환불 요청/승인/거절 API")
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @Operation(summary = "정찰제 즉시구매",
            description = "정찰제 상품을 즉시 구매한다. 결제는 포인트로만 처리되며, "
                    + "결제 금액은 즉시 거래 대금 보관(tradeEscrow)으로 옮겨진다.")
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
            description = "주문 1건을 상세 조회한다. 해당 주문의 구매자/판매자만 조회할 수 있다.")
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

    @Operation(summary = "주문 배송지 등록/수정",
            description = "구매자가 배송지를 등록/수정한다. 판매자가 송장을 등록하기 전(PAID 상태)까지만 가능하다.")
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

    @Operation(summary = "주문 배송지 조회",
            description = "구매자·판매자 모두 조회할 수 있다.")
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

    @Operation(summary = "송장 등록",
            description = "판매자가 PAID 상태인 주문의 송장 정보를 등록한다.\n"
                    + "deliveryapi.co.kr 웹훅 구독에 성공하면 실제 배송완료 신호를 받아야 DELIVERED로 바뀐다.\n"
                    + "구독에 실패하면 등록과 동시에 배송 완료(DELIVERED)까지 반영되는 즉시-확정 방식으로 폴백한다.\n"
                    + "DELIVERED로 바뀌는 시점부터 3일 뒤 자동 구매 확정 시각이 계산된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "PAID 상태가 아니거나 배송지 미등록"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "판매자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{orderId}/shipment")
    public ResponseEntity<ApiResponse<OrderShipmentResponse>> registerShipment(
            Authentication authentication, @PathVariable Long orderId,
            @Valid @RequestBody OrderShipmentRegisterRequest request) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.registerShipment(orderId, memberId, request)));
    }

    @Operation(summary = "구매 확정 처리",
            description = "DELIVERED 상태인 주문의 구매를 확정한다.\n"
                    + "tradeEscrow에 보관된 대금이 판매자에게 정산되고 주문 상태가 SETTLED로 바뀐다(거래 완료).\n 배송 완료 후 3일이 지나면 자동으로도 처리된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "확정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "DELIVERED 상태가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "구매자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{orderId}/confirmation")
    public ResponseEntity<ApiResponse<OrderListItemResponse>> confirmOrder(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.confirmOrder(orderId, memberId)));
    }

    @Operation(summary = "송장 정보 조회",
            description = "구매자·판매자 모두 조회할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문 또는 미등록 송장")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{orderId}/shipment")
    public ResponseEntity<ApiResponse<OrderShipmentResponse>> getShipment(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(orderService.getShipment(orderId, memberId)));
    }
}