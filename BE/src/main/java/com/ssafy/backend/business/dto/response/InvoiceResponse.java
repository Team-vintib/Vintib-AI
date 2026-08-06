package com.ssafy.backend.business.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record InvoiceResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "10") Long orderId,
        @Schema(example = "1234567890") String businessNumber,
        @Schema(example = "빈티브 상회") String businessName,
        @Schema(example = "홍길동") String representativeName,
        @Schema(example = "100000") Long supplyAmount,
        @Schema(example = "10000") Long taxAmount,
        @Schema(example = "110000") Long totalAmount,
        @Schema(example = "2026-08-02T12:00:00") LocalDateTime issuedAt) {
}
