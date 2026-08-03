package com.ssafy.backend.tryon.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record TryOnProfileUploadUrlRequest(

        @Schema(example = "image/jpeg")
        @NotBlank
        String contentType) {
}
