package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record ProductPreUploadUrlRequest(

        @Schema(example = "photo.jpg")
        @NotBlank
        String fileName,

        @Schema(example = "image/jpeg")
        @NotBlank
        String contentType) {
}
