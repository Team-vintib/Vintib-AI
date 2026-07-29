package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

public record ProductCreateRequest(

        @Schema(example = "빈티지 리바이스 데님 자켓")
        @NotBlank
        String title,

        @Schema(example = "1990년대 리바이스 데님 자켓, 상태 양호")
        String description,

        @Schema(example = "1")
        Long categoryId,

        @Schema(example = "1")
        Long brandId,

        @Schema(example = "A")
        String conditionGrade,

        @Schema(example = "M")
        String sizeLabel) {
}
