package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record ProductClassifyStatusResponse(
        @Schema(description = "PENDING/PROCESSING=진행 중, COMPLETED=완료, FAILED=실패") ProductClassifyStatus status,
        @Schema(description = "status=COMPLETED일 때만 값 존재") ProductClassifyResultResponse result,
        @Schema(description = "status=FAILED일 때만 값 존재") String error) {

    public static ProductClassifyStatusResponse pending(ProductClassifyStatus status) {
        return new ProductClassifyStatusResponse(status, null, null);
    }

    public static ProductClassifyStatusResponse failed(String error) {
        return new ProductClassifyStatusResponse(ProductClassifyStatus.FAILED, null, error);
    }

    public static ProductClassifyStatusResponse completed(ProductClassifyResultResponse result) {
        return new ProductClassifyStatusResponse(ProductClassifyStatus.COMPLETED, result, null);
    }
}
