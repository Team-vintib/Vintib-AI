package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * {@code POST /quality/inspections} job payload
 * (`docs/requests/BE/041-quality-inspection-integration.md` §2).
 *
 * <p>{@code base_color}는 보내지 않는다 — AI 쪽 기본값(LIGHT)을 그대로 쓴다(BE는 판매자가 입력한
 * 자유 텍스트 색상만 갖고 있어 AI의 3분류(LIGHT/DARK/PATTERNED)로 신뢰성 있게 매핑할 수 없다).
 */
public record QualityInspectionJobRequest(
        @JsonProperty("product_id") Long productId,
        @JsonProperty("image_urls") List<String> imageUrls,
        String category,
        @JsonProperty("include_descriptions") boolean includeDescriptions,
        @JsonProperty("include_attention_maps") boolean includeAttentionMaps,
        @JsonProperty("include_annotated_images") boolean includeAnnotatedImages) {
}
