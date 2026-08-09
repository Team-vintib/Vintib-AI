package com.ssafy.backend.product.dto.response;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * AI 원본({@code PricingResult}) 조립 테스트.
 *
 * <p>운영에서 상품 상세가 500 으로 죽은 사고를 막기 위한 회귀 테스트다. AI 는
 * {@code rationale} 을 {@code list[str]} 로 주는데 BE 가 {@code (String)} 으로 캐스팅해
 * {@code ClassCastException} 이 났고, AI 시세가 산정된 상품은 조회가 전부 실패했다.
 */
class ProductPriceEstimateResponseTest {

    /** AI 가 실제로 주는 모양(AI/app/pricing/pricer.py 의 _rationale). */
    private Map<String, Object> aiResult() {
        Map<String, Object> result = new HashMap<>();
        result.put("priced", true);
        result.put("price_range", Map.of("min", 40000, "mid", 45000, "max", 50000));
        result.put("confidence", 0.72);
        result.put("confidence_level", "MEDIUM");
        result.put("rationale", List.of(
                "비교 매물 12건의 중앙값은 45,000원입니다.",
                "컨디션 A(4점)을 반영해 계수 1.05를 적용했습니다."));
        result.put("comps_used", List.of(
                Map.of("title", "리바이스 501", "price", 44000, "source", "번개장터", "url", "https://x")));
        result.put("notes", List.of("표본이 적습니다."));
        return result;
    }

    @Test
    void 문장_리스트로_오는_산정_근거를_한_문단으로_이어_붙인다() {
        ProductPriceEstimateResponse response = ProductPriceEstimateResponse.from(aiResult());

        assertThat(response.rationale())
                .isEqualTo("비교 매물 12건의 중앙값은 45,000원입니다. 컨디션 A(4점)을 반영해 계수 1.05를 적용했습니다.");
    }

    @Test
    void 산정_근거가_리스트여도_나머지_필드가_정상_조립된다() {
        ProductPriceEstimateResponse response = ProductPriceEstimateResponse.from(aiResult());

        assertThat(response.priced()).isTrue();
        assertThat(response.priceRange().mid()).isEqualTo(45_000L);
        assertThat(response.confidence()).isEqualTo(0.72);
        assertThat(response.confidenceLevel()).isEqualTo("MEDIUM");
        assertThat(response.compsUsed()).hasSize(1);
        assertThat(response.compsUsed().get(0).title()).isEqualTo("리바이스 501");
        assertThat(response.notes()).containsExactly("표본이 적습니다.");
    }

    @Test
    void 산정_근거가_문자열로_와도_그대로_쓴다() {
        // AI 계약이 되돌아가거나 예전 형식으로 저장된 상품이 있어도 읽을 수 있어야 한다.
        Map<String, Object> result = aiResult();
        result.put("rationale", "한 문장으로 온 근거입니다.");

        assertThat(ProductPriceEstimateResponse.from(result).rationale())
                .isEqualTo("한 문장으로 온 근거입니다.");
    }

    @Test
    void 산정_근거가_없으면_null이다() {
        Map<String, Object> result = aiResult();
        result.remove("rationale");

        assertThat(ProductPriceEstimateResponse.from(result).rationale()).isNull();
    }

    @Test
    void 빈_리스트로_오면_빈_문자열이_아니라_null이다() {
        // FE 는 rationale 이 있을 때만 문단을 그린다. 빈 문자열이면 빈 줄이 남는다.
        Map<String, Object> result = aiResult();
        result.put("rationale", List.of());

        assertThat(ProductPriceEstimateResponse.from(result).rationale()).isNull();
    }

    @Test
    void 예상치_못한_타입이_와도_상세_조회를_막지_않는다() {
        // 그 필드만 비고 화면은 떠야 한다 — 상세 조회 전체가 죽는 것이 이번 사고의 원인이었다.
        Map<String, Object> result = aiResult();
        result.put("rationale", 12345);
        result.put("confidence_level", List.of("MEDIUM"));

        assertThatCode(() -> ProductPriceEstimateResponse.from(result)).doesNotThrowAnyException();
        assertThat(ProductPriceEstimateResponse.from(result).rationale()).isNull();
        assertThat(ProductPriceEstimateResponse.from(result).confidenceLevel()).isEqualTo("MEDIUM");
    }
}
