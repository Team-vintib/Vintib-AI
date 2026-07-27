package com.ssafy.backend.product.dto.request;

import jakarta.validation.constraints.NotBlank;

public record ProductCreateRequest(
        @NotBlank String title,
        String description,
        Long categoryId,
        Long brandId,
        String conditionGrade,
        String sizeLabel) {
}
