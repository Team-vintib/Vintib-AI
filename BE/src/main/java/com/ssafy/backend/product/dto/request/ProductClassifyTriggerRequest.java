package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record ProductClassifyTriggerRequest(

        @Schema(example = "pre-upload/7/3f2a9c1e-....jpg")
        @NotBlank
        String key) {
}
