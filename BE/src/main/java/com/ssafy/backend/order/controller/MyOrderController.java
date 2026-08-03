package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.order.dto.request.OrderRole;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// 마이페이지 구매/낙찰 내역(MY-003), 판매/정산 내역(MY-004). 기존 OrderController(/api/orders,
// 상세 조회)와 경로 prefix가 달라 별도 컨트롤러로 분리한다(MyProductController와 같은 이유).
@Tag(name = "마이페이지(MyPage)", description = "마이페이지 도메인별 요약/관리 API")
@RestController
@RequestMapping("/api/users/{userId}/orders")
@RequiredArgsConstructor
public class MyOrderController {

    private final OrderService orderService;

    @Operation(summary = "주문 목록 조회",
            description = "본인 주문 목록을 최신순으로 조회한다. role=BUYER면 구매/낙찰 내역(MY-003), "
                    + "role=SELLER면 판매/정산 내역(MY-004)이다. 정산 완료 여부는 status가 SETTLED인지로 판단하며, "
                    + "정산액은 수수료 없이 orderPrice 그대로다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "role 파라미터 누락 또는 잘못된 값"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 주문 목록을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<OrderListItemResponse>>> getOrders(
            Authentication authentication, @PathVariable Long userId,
            @RequestParam OrderRole role, @PageableDefault(size = 20) Pageable pageable) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(orderService.getOrders(userId, role, pageable)));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }
    }
}
