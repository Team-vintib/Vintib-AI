package com.ssafy.backend.product.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ProductImageRegisterRequest(@NotBlank String key, @NotNull Short sortOrder, boolean isPrimary) {
}