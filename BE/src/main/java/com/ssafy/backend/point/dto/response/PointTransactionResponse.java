package com.ssafy.backend.point.dto.response;

import com.ssafy.backend.point.entity.PointTransaction;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record PointTransactionResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "CHARGE") String type,
        @Schema(description = "부호 있는 증감액", example = "100000") Long amount,
        @Schema(example = "100000") Long balanceAfter,
        @Schema(example = "null") String refType,
        @Schema(example = "null") Long refId,
        @Schema(example = "2026-08-03T12:00:00") LocalDateTime createdAt) {

    public static PointTransactionResponse from(PointTransaction transaction) {
        return new PointTransactionResponse(
                transaction.getId(),
                transaction.getType().name(),
                transaction.getAmount(),
                transaction.getBalanceAfter(),
                transaction.getRefType(),
                transaction.getRefId(),
                transaction.getCreatedAt());
    }
}