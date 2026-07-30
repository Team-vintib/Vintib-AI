package com.ssafy.backend.product.dto.request;

import jakarta.validation.constraints.Size;

public record ProductUpdateRequest(
        @Size(min = 1) String title,
        String description,
        Long categoryId,
        Long brandId,
        String conditionGrade,
        String sizeLabel) {
}