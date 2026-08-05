package com.ssafy.backend.point.dto.response;

import com.ssafy.backend.point.entity.WithdrawalAccount;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record WithdrawalAccountResponse(
        @Schema(example = "국민은행") String bankName,
        @Schema(example = "123456-78-901234") String accountNumber,
        @Schema(example = "홍길동") String accountHolderName,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime updatedAt) {

    public static WithdrawalAccountResponse from(WithdrawalAccount account) {
        return new WithdrawalAccountResponse(
                account.getBankName(),
                account.getAccountNumber(),
                account.getAccountHolderName(),
                account.getUpdatedAt());
    }
}