package com.ssafy.backend.product.dto.request;

import com.ssafy.backend.product.entity.SaleType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * GET /api/products 필터·정렬 파라미터 묶음 (PROD-008).
 * null 이면 해당 조건을 건너뛴다.
 */
public record ProductListFilterParams(

        @Schema(description = "카테고리 ID 목록 (여러 개 가능). 미입력 시 전체 카테고리", example = "1,2")
        List<Long> categoryIds,

        @Schema(description = "상태 등급 목록 (여러 개 가능). 미입력 시 전체 등급", example = "S,A")
        List<String> conditionGrades,

        @Schema(description = "판매 방식. DIRECT_SALE 또는 AUCTION. 미입력 시 전체", example = "DIRECT_SALE")
        SaleType saleType,

        @Schema(description = "최소 가격 (원). 미입력 시 하한 없음", example = "10000")
        Long minPrice,

        @Schema(description = "최대 가격 (원). 미입력 시 상한 없음", example = "100000")
        Long maxPrice,

        @Schema(description = "정렬 기준. LATEST(기본값) / PRICE_ASC / PRICE_DESC", example = "LATEST")
        ProductSortType sort,

        @Schema(description = "판매자 회원 ID. 특정 판매자의 상품만 본다(공개 프로필용, 011 §3.5). 미입력 시 전체", example = "10")
        Long sellerId
) {
    /**
     * 각 파라미터가 필터로 활성화됐는지 판단하는 헬퍼들.
     * JPQL 선택적 필터 패턴에서 boolean 플래그로 활용한다.
     */
    public boolean hasCategoryFilter() {
        return categoryIds != null && !categoryIds.isEmpty();
    }

    public boolean hasSellerFilter() {
        return sellerId != null;
    }

    public boolean hasConditionFilter() {
        return conditionGrades != null && !conditionGrades.isEmpty();
    }

    public boolean hasSaleTypeFilter() {
        return saleType != null;
    }

    public boolean hasMinPriceFilter() {
        return minPrice != null;
    }

    public boolean hasMaxPriceFilter() {
        return maxPrice != null;
    }

    /** sort 가 null 이거나 명시되지 않으면 LATEST 를 기본값으로 쓴다. */
    public ProductSortType resolvedSort() {
        return sort != null ? sort : ProductSortType.LATEST;
    }
}
