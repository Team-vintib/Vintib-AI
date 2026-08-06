package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.AiModelCutStatus;
import com.ssafy.backend.product.entity.Product;
import io.swagger.v3.oas.annotations.media.Schema;

public record ProductAiModelCutResponse(
        @Schema(description = "NONE=미사용, PENDING/PROCESSING=생성 중, COMPLETED=완료, FAILED=실패",
                example = "PROCESSING")
                AiModelCutStatus status,
        @Schema(description = "status=COMPLETED일 때만 값 존재", example = "https://.../results/tryon-results/xxx.png")
                String imageUrl) {

    public static ProductAiModelCutResponse from(Product product) {
        return new ProductAiModelCutResponse(product.getAiModelCutStatus(), product.getAiModelCutImageUrl());
    }
}
