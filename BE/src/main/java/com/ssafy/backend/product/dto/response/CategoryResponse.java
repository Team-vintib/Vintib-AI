package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Category;
import io.swagger.v3.oas.annotations.media.Schema;

public record CategoryResponse(

        @Schema(example = "1") Long id,
        @Schema(example = "1") Long parentId,
        @Schema(example = "티셔츠") String name,
        @Schema(example = "TSHIRT") String nameEn,
        @Schema(example = "1") Short depth) {

    public static CategoryResponse from(Category category) {
        return new CategoryResponse(
                category.getId(), category.getParentId(), category.getName(), category.getNameEn(), category.getDepth());
    }
}
