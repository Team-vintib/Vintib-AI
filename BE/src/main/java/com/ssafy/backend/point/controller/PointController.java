package com.ssafy.backend.point.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.point.dto.request.PointChargeConfirmRequest;
import com.ssafy.backend.point.dto.request.PointChargeRequest;
import com.ssafy.backend.point.dto.request.WithdrawalAccountRequest;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointChargeReadyResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
import com.ssafy.backend.point.dto.response.WithdrawalAccountResponse;
import com.ssafy.backend.point.service.PointService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 마이페이지 포인트/출금 관리(MY-007). 출금 신청/내역은 별도 리소스라 WithdrawalController가 담당한다
// 충전은 토스페이먼츠 결제위젯 준비(ready)/승인(confirm) 2단계로 처리한다(POINT-001).
@Tag(name = "포인트 / 계좌 / 출금 (Wallet)", description = "포인트 잔액/충전, 출금 신청/내역 API")
@RestController
@RequestMapping("/api/users/{userId}/points")
@RequiredArgsConstructor
public class PointController {

    private final PointService pointService;

    @Operation(summary = "포인트 잔액 조회",
            description = "본인의 포인트 잔액을 버킷별로 조회한다. 계정이 없으면 이 조회에서 0 잔액으로 생성된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 잔액을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PointBalanceResponse>> getBalance(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.getBalance(userId)));
    }

    @Operation(summary = "포인트 사용 내역 조회", description = "본인의 포인트 원장을 최신순으로 조회한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 내역을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/logs")
    public ResponseEntity<ApiResponse<PageResponse<PointTransactionResponse>>> getTransactions(
            Authentication authentication, @PathVariable Long userId, @PageableDefault(size = 20) Pageable pageable) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.getTransactions(userId, pageable)));
    }

    @Operation(summary = "포인트 충전 준비",
            description = "토스페이먼츠 결제위젯에 넘길 orderId를 발급받는다. 결제위젯 호출 후 /charges/confirm으로 승인한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "충전 준비 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 충전을 준비하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/charges/ready")
    public ResponseEntity<ApiResponse<PointChargeReadyResponse>> readyCharge(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody PointChargeRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.readyCharge(userId, request.amount())));
    }

    @Operation(summary = "포인트 충전 승인",
            description = "결제위젯에서 받은 paymentKey로 토스 결제 승인을 요청하고, 성공하면 잔액에 반영한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "충전 승인 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400",
                    description = "요청값 검증 실패, 결제 금액 불일치, 이미 처리된 결제, 또는 토스 결제 승인 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 충전을 승인하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 결제 준비 정보")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/charges/confirm")
    public ResponseEntity<ApiResponse<PointBalanceResponse>> confirmCharge(
            Authentication authentication, @PathVariable Long userId,
            @Valid @RequestBody PointChargeConfirmRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(
                pointService.confirmCharge(userId, request.orderId(), request.paymentKey(), request.amount())));
    }

    @Operation(summary = "출금 계좌 등록/수정",
            description = "출금(현금화) 계좌 정보를 등록하거나 수정한다(POINT-003). 실제 은행 송금 연동은 범위 밖이며 계좌 정보만 남긴다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록/수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 계좌를 등록하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PutMapping("/account")
    public ResponseEntity<ApiResponse<WithdrawalAccountResponse>> registerWithdrawalAccount(
            Authentication authentication, @PathVariable Long userId,
            @Valid @RequestBody WithdrawalAccountRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.registerWithdrawalAccount(
                userId, request.bankName(), request.accountNumber(), request.accountHolderName())));
    }

    @Operation(summary = "출금 계좌 조회", description = "등록된 출금(현금화) 계좌 정보를 조회한다(POINT-003).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 계좌를 조회하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "등록된 출금 계좌가 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/account")
    public ResponseEntity<ApiResponse<WithdrawalAccountResponse>> getWithdrawalAccount(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.getWithdrawalAccount(userId)));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
    }
}