package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

public record ProductUpdateRequest(
        @Size(min = 1) String title,
        String description,
        Long categoryId,

        @Schema(description = "브랜드명. 마스터에서 고르지 않고 자유 텍스트로 받는다", example = "Maison Kitsuné")
        String brand,
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
                description = "판매자가 \"하자 아님\"으로 표시한 AI 품질 검수 finding의 key 목록(CH002)."
                        + " 원본(quality_inspection_result)은 그대로 두고 이 key들만 상세 응답에서"
                        + " isExcluded=true로 표시한다. 전체 교체 — null이면 미반영, 빈 배열이면 기존"
                        + " 제외 목록을 전부 해제한다. 검수 job이 등록(POST) 이후에 끝나므로 PATCH 전용이다.",
                example = "[\"hole_tear_0_2_1\"]")
        List<String> excludedQualityFindingKeys,

        @Schema(
                description = "정찰제 가격 조정. null이면 미반영. 경매 상품(saleType=AUCTION)은 가격 개념이"
                        + " 없어 반영하지 않고 400을 반환한다 — 경매 시작가는 별도 API(AUCT)에서 다룬다.",
                example = "89000")
        @Positive
        Long price,

        @Schema(
                description = "AI 시세 조회가 계산한 '동일 상품' 판정 키. FE가 GET /ai/jobs/{jobId} "
                        + "폴링 결과(product_match_key)를 그대로 전달한다. null이면 미반영",
                example = "1:501-리바이스:97")
        String matchKey) {
}