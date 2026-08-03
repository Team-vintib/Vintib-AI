package com.ssafy.backend.point.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.point.dto.request.PointWithdrawalRequest;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
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
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 출금 신청/내역(MY-007, POINT-004). points 하위가 아니라 독립 리소스로 확정(APIs.md).
// 관리자 승인 체계가 없어 신청까지만 처리한다 — 완료 처리는 DB 직접 조작.
@Tag(name = "포인트/출금(Wallet)", description = "포인트 잔액/충전, 출금 신청/내역 API")
@RestController
@RequestMapping("/api/users/{userId}/withdrawals")
@RequiredArgsConstructor
public class WithdrawalController {

    private final PointService pointService;

    @Operation(summary = "출금 신청",
            description = "잔액에서 출금을 신청한다(신청까지만 처리 — 완료 처리는 범위 밖). available 잔액이 부족하면 400으로 거부된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "출금 신청 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잔액 부족 또는 요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 출금을 신청하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<PointBalanceResponse>> requestWithdrawal(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody PointWithdrawalRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.requestWithdrawal(userId, request.amount())));
    }

    @Operation(summary = "출금 내역 조회", description = "본인의 출금 신청 내역을 최신순으로 조회한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 출금 내역을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<PointTransactionResponse>>> getWithdrawals(
            Authentication authentication, @PathVariable Long userId, @PageableDefault(size = 20) Pageable pageable) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.getWithdrawals(userId, pageable)));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
    }
}
