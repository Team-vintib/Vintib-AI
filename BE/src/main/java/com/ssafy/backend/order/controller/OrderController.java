package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 주문 단건 리소스(MY-003 상세). 경로에 userId가 없어 requireSelf 패턴 대신 서비스 내부
// Order.isPartyOf(principal)에 권한 확인을 위임한다(InvoiceController와 동일한 이유).
@Tag(name = "주문(Orders)", description = "주문 조회 API")
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

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
}
