package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 유사 상품 추천 응답(CH034). AI CLIP 임베딩 배치 캐시를 우선 쓰고, 부족하면 카테고리/브랜드
 * SQL로 보충한다 — 요청 시점에 AI를 호출하지 않는다({@code docs/requests/BE/042}).
 */
public record SimilarProductsResponse(
        @Schema(example = "42") Long productId,
        @Schema(description = "유사도 높은 순(AI 캐시 우선, 부족분은 SQL 폴백으로 보충)")
        List<ProductResponse> items) {
}
