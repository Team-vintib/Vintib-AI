package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ProductCreateRequest(

        @Schema(example = "빈티지 리바이스 데님 자켓")
        @NotBlank
        String title,

        @Schema(example = "1990년대 리바이스 데님 자켓, 상태 양호")
        String description,

        @Schema(description = "카테고리 ID. 필수다", example = "1")
        @NotNull
        Long categoryId,

        @Schema(example = "1")
        Long brandId,

        @Schema(example = "A")
        String conditionGrade,

        @Schema(example = "M")
        String sizeLabel) {
}