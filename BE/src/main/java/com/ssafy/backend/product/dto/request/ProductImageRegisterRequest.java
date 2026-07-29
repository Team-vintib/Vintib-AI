package com.ssafy.backend.product.dto.request;

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
        boolean isPrimary) {
}