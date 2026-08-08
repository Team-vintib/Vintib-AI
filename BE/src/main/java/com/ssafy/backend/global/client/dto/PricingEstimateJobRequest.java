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
        @JsonProperty("condition_score") Double conditionScore,
        @JsonProperty("condition_grade") String conditionGrade) {
}
