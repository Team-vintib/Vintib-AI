package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record ProductStatusUpdateRequest(

        @Schema(example = "50000")
        @NotNull
        @Positive
        Long price) {
}