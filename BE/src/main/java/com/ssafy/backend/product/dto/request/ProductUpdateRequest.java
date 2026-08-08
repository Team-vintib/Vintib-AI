package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

public record ProductUpdateRequest(
        @Size(min = 1) String title,
        String description,
        Long categoryId,
        Long brandId,
        String conditionGrade,
        String sizeLabel,

        @Schema(example = "BLACK") String color,

        @Schema(example = "Cotton 100%") String material,

        @Schema(description = "실측 치수(cm). null이면 미반영", example = "{\"총장\": 70, \"어깨너비\": 45}")
        Map<String, Integer> measurements,

        @Schema(
                description = "하자 목록 전체 교체. null이면 미반영, 빈 배열이면 기존 하자를 전부 삭제한다.",
                example = "[\"소매 끝 실밥 풀림\"]")
        List<String> defects,

        @Schema(
                description = "AI 품질 검수에서 사용자가 하자로 인정하고 확정한 finding 목록 전체 교체."
                        + " null이면 미반영, 빈 배열이면 기존 finding을 전부 삭제한다. DRAFT로 먼저 만든"
                        + " 상품처럼 등록(POST) 시점에는 확정 전이라 못 보낸 finding을 최종 제출(PATCH)"
                        + " 시점에 보낼 때 쓴다.")
        @Valid
        List<AiQualityFindingRequest> aiQualityFindings,

        @Schema(
                description = "상시 판매 가격 조정. null이면 미반영. 경매 상품(saleType=AUCTION)은 가격 개념이"
                        + " 없어 반영하지 않고 400을 반환한다 — 경매 시작가는 별도 API(AUCT)에서 다룬다.",
                example = "89000")
        @Positive
        Long price) {
}