package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/** {@code POST /products/price-estimates} 응답 — 결과가 아니라 접수증. */
public record PriceEstimateJobResponse(
        @Schema(
                description = "GET /ai/jobs/{jobId}로 FE가 직접 폴링할 job id. "
                        + "BE는 이 값을 다시 조회하지 않는다.",
                example = "3f2a-1234-5678")
        String jobId) {
}