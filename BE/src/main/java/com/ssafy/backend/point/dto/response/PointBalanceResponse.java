package com.ssafy.backend.point.dto.response;

import com.ssafy.backend.point.entity.PointAccount;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record PointBalanceResponse(
        @Schema(description = "사용 가능 잔액", example = "100000") Long available,
        @Schema(description = "입찰 보류", example = "0") Long bidHeld,
        @Schema(description = "거래 대금 보관", example = "0") Long tradeEscrow,
        @Schema(description = "판매자 정산 대기", example = "0") Long settling,
        @Schema(description = "출금 처리 중", example = "0") Long withdrawing,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime updatedAt) {

    public static PointBalanceResponse from(PointAccount account) {
        return new PointBalanceResponse(
                account.getAvailable(),
                account.getBidHeld(),
                account.getTradeEscrow(),
                account.getSettling(),
                account.getWithdrawing(),
                account.getUpdatedAt());
    }
}