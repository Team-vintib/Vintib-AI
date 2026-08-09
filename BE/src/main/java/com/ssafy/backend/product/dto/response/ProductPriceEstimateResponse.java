package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

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
        @Schema(description = "산정 근거 요약. AI 는 문장 여러 개로 주고 여기서 한 문단으로 이어 붙인다")
        String rationale,
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
                asText(result.get("confidence_level")),
                asText(result.get("rationale")),
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
                asText(raw.get("title")), asLong(raw.get("price")), asText(raw.get("source")), asText(raw.get("url")));
    }

    /**
     * AI 원본의 값 하나를 화면에 쓸 문자열로 만든다.
     *
     * <p><b>리스트를 받는 이유.</b> {@code rationale} 은 AI 쪽 계약이 {@code list[str]} 이다
     * ({@code AI/app/pricing/schemas.py} 의 {@code PricingResult}). 이걸 {@code (String)} 으로
     * 캐스팅하다 {@code ClassCastException} 이 나 <b>상품 상세 조회가 통째로 500 이 됐다</b> —
     * AI 시세가 산정된 상품은 예외 없이 실패했다.
     *
     * <p>원소는 각각 완결된 문장이라 공백으로 이으면 한 문단이 된다. FE 계약은
     * {@code string | null} 그대로 유지되므로 FE 는 고칠 것이 없다.
     *
     * <p>같은 사고를 막으려고 이 클래스의 문자열 추출은 전부 이 메서드를 거친다. AI 가 타입을
     * 또 바꾸더라도 <b>그 필드만 비고 화면은 뜬다</b> — 상세 조회 전체가 죽는 것보다 낫다.
     */
    private static String asText(Object value) {
        if (value instanceof List<?> list) {
            return list.isEmpty() ? null : list.stream().map(String::valueOf).collect(Collectors.joining(" "));
        }
        return value instanceof String text ? text : null;
    }

    private static Long asLong(Object value) {
        return value instanceof Number number ? number.longValue() : null;
    }

    private static Double asDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }
}
