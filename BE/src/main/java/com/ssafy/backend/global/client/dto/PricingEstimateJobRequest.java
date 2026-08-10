package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * {@code POST /pricing/estimates} job payload
 * (`docs/requests/BE/044-pricing-estimate-trigger.md`).
 *
 * <p>{@code retail_price}/{@code include_retail}/{@code image_url}은 이 트리거 범위에서 쓰지
 * 않는다 — 신상품가 조회는 기본 꺼짐(AI 쪽 기본값 그대로), {@code internal_clip} comps 백엔드는
 * 아직 활성화하지 않아 이미지가 필요 없다.
 */
public record PricingEstimateJobRequest(
        @JsonProperty("product_id") Long productId,
        @JsonProperty("product_name") String productName,
        String brand,
        String category,
        // AI 6종 GarmentCategory(category)와 별개로 BE 원본 categoryId도 그대로 보낸다 —
        // internal_text comps 백엔드가 product_corpus(BE categoryId 기준 캐시)와 같은 체계로
        // 매칭 키를 만드는 데 필요하다. 없으면 AI가 internal_text 매칭을 포기한다(CH0xx).
        @JsonProperty("category_id") Long categoryId,
        @JsonProperty("condition_score") Double conditionScore,
        @JsonProperty("condition_grade") String conditionGrade) {
}
