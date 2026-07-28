package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Category;

public record CategoryResponse(Long id, Long parentId, String name, Short depth) {

    public static CategoryResponse from(Category category) {
        return new CategoryResponse(
                category.getId(), category.getParentId(), category.getName(), category.getDepth());
    }
}
