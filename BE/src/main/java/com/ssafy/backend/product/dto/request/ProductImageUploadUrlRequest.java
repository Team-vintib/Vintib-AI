package com.ssafy.backend.product.dto.request;

import jakarta.validation.constraints.NotBlank;

public record ProductImageUploadUrlRequest(@NotBlank String fileName, @NotBlank String contentType) {
}