package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.Map;

/**
 * 상품 상세 "AI 시세 추천" 카드(CH003). 등록 시 확정 등급으로 조회한 AI
 * {@code PricingResult} 원본({@link com.ssafy.backend.product.entity.Product#getPriceEstimateResult()})에서
 * 화면에 필요한 값만 추려 조립한다 — {@code AiQualityFindingResponse}와 같은 "원본 저장 + 읽을
 * 때 조립" 패턴이다.
 */
public record ProductPriceEstimateResponse(
        @Schema(description = "가격을 산정할 수 있었는지(comps 부족 등으로 실패할 수 있음)") boolean priced,
        PriceRange priceRange,
        @Schema(description = "0~1, comps 표본·분산 기반 신뢰도") Double confidence,
        @Schema(example = "MEDIUM") String confidenceLevel,
        @Schema(description = "산정 근거 요약") String rationale,
        List<Comp> compsUsed,
        List<String> notes) {

    public record PriceRange(Long min, Long mid, Long max) {
    }

    public record Comp(String title, Long price, String source, String url) {
    }

    @SuppressWarnings("unchecked")
    public static ProductPriceEstimateResponse from(Map<String, Object> result) {
        Map<String, Object> rawPriceRange = (Map<String, Object>) result.get("price_range");
        List<Map<String, Object>> rawComps =
                (List<Map<String, Object>>) result.getOrDefault("comps_used", List.of());
        List<String> notes = (List<String>) result.getOrDefault("notes", List.of());

        return new ProductPriceEstimateResponse(
                Boolean.TRUE.equals(result.get("priced")),
                toPriceRange(rawPriceRange),
                asDouble(result.get("confidence")),
                (String) result.get("confidence_level"),
                (String) result.get("rationale"),
                rawComps.stream().map(ProductPriceEstimateResponse::toComp).toList(),
                notes);
    }

    private static PriceRange toPriceRange(Map<String, Object> raw) {
        if (raw == null) {
            return null;
        }
        return new PriceRange(asLong(raw.get("min")), asLong(raw.get("mid")), asLong(raw.get("max")));
    }

    private static Comp toComp(Map<String, Object> raw) {
        return new Comp(
                (String) raw.get("title"), asLong(raw.get("price")), (String) raw.get("source"), (String) raw.get("url"));
    }

    private static Long asLong(Object value) {
        return value instanceof Number number ? number.longValue() : null;
    }

    private static Double asDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }
}
