package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 상품 등록 화면 "AI 가격 추천" 경량 트리거 요청
 *
 * <p>실제로 생성된 상품이 없어도 호출할 수 있다 — FE가 등급(S/A/B/C)별로 나눠 여러 번 호출해
 * 등급별 추천가를 만드는 용도.
 */
public record PriceEstimateRequest(

        @Schema(example = "메종키츠네 폭스 패치 티셔츠")
        @NotBlank
        @Size(max = 200)
        String productName,

        @Schema(
                description = "카테고리 ID. 선택 — 있으면 AI 쪽 6종 GarmentCategory로 매핑해서 보낸다"
                        + "(대응값이 없는 카테고리면 매핑 없이 진행).",
                example = "1")
        Long categoryId,

        @Schema(example = "메종키츠네")
        @Size(max = 100)
        String brand,

        @Schema(description = "AI 품질 검수가 매긴 상태 원점수(0~100)", example = "82.0")
        @NotNull
        @DecimalMin("0.0")
        @DecimalMax("100.0")
        Double conditionScore,

        @Schema(description = "상태 등급. S/A/B/C만 허용", example = "A")
        @NotBlank
        @Pattern(regexp = "^(S|A|B|C)$")
        String conditionGrade,

        @Schema(
                description = "이미 생성된 상품이 있으면 그 ID. 없으면 비워도 된다(BE가 임시값으로 대체).",
                example = "42")
        Long productId) {
}