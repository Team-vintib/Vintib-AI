package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

public record ProductImageUpdateRequest(

        @Schema(example = "1")
        Short sortOrder,

        @Schema(example = "true")
        Boolean isPrimary) {
}