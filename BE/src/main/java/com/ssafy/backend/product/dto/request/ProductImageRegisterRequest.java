package com.ssafy.backend.product.dto.request;

import com.ssafy.backend.product.entity.ProductImageRole;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ProductImageRegisterRequest(

        @Schema(example = "product-images/1/abc123.jpg")
        @NotBlank
        String key,

        @Schema(example = "0")
        @NotNull
        Short sortOrder,

        @Schema(example = "true")
        boolean isPrimary,

        @Schema(
                description = "이미지 용도. FRONT/BACK은 AI 품질 검수용 앞/뒤 사진(상품당 하나씩만 등록 가능), "
                        + "ADDITIONAL은 그 외 참고 사진.",
                example = "FRONT")
        @NotNull
        ProductImageRole role) {
}
