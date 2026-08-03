package com.ssafy.backend.order.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.order.dto.response.InvoiceResponse;
import com.ssafy.backend.order.service.InvoiceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 경로에 {userId}가 없어 requireSelf 패턴 대신 서비스 내부에서 Order.isPartyOf(principal)로
// 권한을 확인한다(구매자/판매자 둘 다 호출 가능).
@Tag(name = "사업자(Businesses)", description = "사업자 인증 정보 제출/조회 API")
@RestController
@RequestMapping("/api/orders/{orderId}/invoices")
@RequiredArgsConstructor
public class InvoiceController {

    private final InvoiceService invoiceService;

    @Operation(summary = "세금계산서 발행",
            description = "주문의 판매자가 사업자 인증(APPROVED)을 완료했을 때 세금계산서를 발행한다. 주문당 1건만 발행할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "발행 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "판매자가 사업자 인증(APPROVED)을 완료하지 않음"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 발행된 세금계산서")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<InvoiceResponse>> issueInvoice(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        InvoiceResponse response = invoiceService.issueInvoice(orderId, memberId);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(summary = "세금계산서 조회", description = "발행된 세금계산서를 조회한다. 해당 주문의 구매자/판매자만 조회할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "해당 주문의 거래 당사자가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 주문 또는 발행된 세금계산서가 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<InvoiceResponse>> getInvoice(
            Authentication authentication, @PathVariable Long orderId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(invoiceService.getInvoice(orderId, memberId)));
    }
}
