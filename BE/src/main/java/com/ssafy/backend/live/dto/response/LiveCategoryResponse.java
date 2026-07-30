package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 라이브 카테고리 응답. 편성 상품의 카테고리를 대분류로 올린 값이다.
 *
 * <p>{@code id}는 카테고리 마스터(`GET /api/categories`)의 ID와 같다 — 목록 화면의 카테고리
 * 필터가 이 값을 그대로 쓴다.
 */
public record LiveCategoryResponse(

        @Schema(description = "카테고리 ID. 카테고리 마스터의 ID와 같다", example = "10")
        Long id,

        @Schema(description = "카테고리명(대분류)", example = "아우터")
        String name
) {

    public static LiveCategoryResponse from(CategorySummary category) {
        return new LiveCategoryResponse(category.id(), category.name());
    }
}