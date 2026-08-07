package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 분류 완료 결과. AI는 소분류 코드(예: "CARDIGAN")만 주고, categoryId는 BE가
 * {@code CategoryIdResolver}(성별 정적 조회표, 남성 우선)로 계산해 함께 내려준다 —
 * `docs/requests/BE/045-classify-pre-upload-integration.md` 참고.
 */
public record ProductClassifyResultResponse(
        @Schema(description = "카테고리 제안. 소분류를 categoryId로 못 옮기면 null") CategorySuggestion category,
        @Schema(description = "주색상 제안(보조색상은 체크포인트가 예측하지 않아 항상 없음)")
                ColorSuggestion colorPrimary,
        @Schema(example = "v2-be-seed-2026-08-03") String taxonomyVersion) {

    public record CategorySuggestion(
            @Schema(description = "depth2(대분류) id", example = "4") Long majorCategoryId,
            @Schema(description = "depth3(소분류) id — 카테고리 드롭다운이 실제로 선택할 값", example = "26")
                    Long categoryId,
            @Schema(example = "autofill") String action,
            @Schema(example = "0.83") double score) {
    }

    public record ColorSuggestion(
            @Schema(description = "색상 팔레트 코드", example = "NAVY") String colorId,
            @Schema(example = "suggest") String action,
            @Schema(example = "0.6") double score) {
    }
}
