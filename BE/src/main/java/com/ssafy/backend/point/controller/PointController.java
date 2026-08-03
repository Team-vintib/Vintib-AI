package com.ssafy.backend.point.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.point.dto.request.PointChargeRequest;
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

// 마이페이지 포인트/출금 관리(MY-007). 출금 신청/내역은 별도 리소스라 WithdrawalController가 담당한다
// (APIs.md 포인트/계좌/출금(Wallet) 섹션 — withdrawals가 points 하위가 아닌 독립 경로로 확정).
// 충전은 결제 연동 없는 테스트/데모 전용이다.
@Tag(name = "마이페이지(MyPage)", description = "마이페이지 도메인별 요약/관리 API")
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

    @Operation(summary = "포인트 충전(테스트/데모 전용)",
            description = "결제 연동 없이 금액만 받아 잔액에 더한다. 실결제 검증이 없는 테스트/데모 전용 엔드포인트다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "충전 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 잔액을 충전하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/charges")
    public ResponseEntity<ApiResponse<PointBalanceResponse>> charge(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody PointChargeRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(pointService.charge(userId, request.amount())));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
    }
}
