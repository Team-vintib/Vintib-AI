package com.ssafy.backend.product.dto.request;

/**
 * 상품 목록 정렬 기준 (PROD-008).
 */
public enum ProductSortType {
    /** 최신 등록 순 (기본값) */
    LATEST,
    /** 가격 낮은 순 */
    PRICE_ASC,
    /** 가격 높은 순 */
    PRICE_DESC
}
