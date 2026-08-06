package com.ssafy.backend.refund.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.refund.dto.request.RefundCreateRequest;
import com.ssafy.backend.refund.dto.request.RefundReviewRequest;
import com.ssafy.backend.refund.dto.response.RefundResponse;
import com.ssafy.backend.refund.service.RefundService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

// 경로에 userId가 없어 requireSelf 패턴 대신 서비스 내부 Order.isBuyer/isSeller/isPartyOf에
// 권한 확인을 위임한다(OrderController/InvoiceController와 동일한 이유).
@Tag(name = "주문 / 배송 / 환불(Orders)", description = "주문 생성/조회, 배송지·송장, 구매 확정, 환불 요청/승인/거절 API")
@RestController
@RequiredArgsConstructor
public class RefundController {

    private final RefundService refundService;

    @Operation(summary = "환불 요청",
            description = "구매자가 환불을 요청한다. 주문이 PAID/SHIPPING/DELIVERED 상태여야 하며, "
                    + "이미 진행 중인(REQUESTED) 환불 요청이 있으면 거부된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "요청 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "환불 요청 불가 상태"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "구매자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 진행 중인 환불 요청이 있음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/api/orders/{orderId}/refunds")
    public ResponseEntity<ApiResponse<RefundResponse>> requestRefund(
            Authentication authentication, @PathVariable Long orderId,
            @Valid @RequestBody RefundCreateRequest request) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(refundService.requestRefund(orderId, memberId, request)));
    }

    @Operation(summary = "환불 요청 목록 조회",
            description = "해당 주문의 환불 요청을 최신순으로 조회한다. 구매자·판매자 모두 조회할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/api/orders/{orderId}/refunds")
    public ResponseEntity<ApiResponse<List<RefundResponse>>> getRefunds(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(refundService.getRefunds(orderId, memberId)));
    }

    @Operation(summary = "환불 승인/거절 처리",
            description = "판매자가 환불 요청을 승인하거나 거절한다. 승인하면 보관 중이던 대금이 판매자에게 정산되지 "
                    + "않고 구매자 available 포인트로 바로 환급되며 주문 상태가 REFUNDED로 바뀐다. 거절하면 주문은 "
                    + "이전 상태 그대로 이어간다. 거절 시 rejectionReason은 필수다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "처리 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "이미 처리됨, 또는 거절 사유 누락"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "판매자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 환불 요청")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/api/refunds/{refundId}")
    public ResponseEntity<ApiResponse<RefundResponse>> reviewRefund(
            Authentication authentication, @PathVariable Long refundId,
            @Valid @RequestBody RefundReviewRequest request) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(refundService.reviewRefund(refundId, memberId, request)));
    }
}