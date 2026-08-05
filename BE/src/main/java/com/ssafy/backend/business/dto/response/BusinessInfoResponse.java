package com.ssafy.backend.business.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record BusinessInfoResponse(
        @Schema(description = "NONE(미제출) | PENDING | APPROVED | REJECTED", example = "PENDING")
        String status,

        @Schema(example = "1234567890") String businessNumber,
        @Schema(example = "빈티브 상회") String businessName,
        @Schema(example = "홍길동") String representativeName,

        @Schema(description = "사업자등록증 presigned GET URL. 미제출이면 null", example = "https://s3.example.com/business-certificates/1/abc123.jpg?X-Amz-...")
        String certificateUrl,

        @Schema(example = "2026-08-02T12:00:00") LocalDateTime submittedAt,
        @Schema(example = "2026-08-03T09:00:00") LocalDateTime verifiedAt) {
}