package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * {@code GET /recommend/products/{id}/similar} 응답(AI, CH034). CLIP 임베딩 코사인 유사도
 * 순(높은 순)으로 정렬돼 있고 자기 자신은 빠져 있다. 카드 메타(제목/가격/썸네일 등)는 안
 * 채워 온다 — BE가 이 id로 직접 채운다.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record SimilarProductAiResponse(@JsonProperty("product_id") Long productId, List<Item> items) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Item(@JsonProperty("product_id") Long productId, double score) {
    }
}
