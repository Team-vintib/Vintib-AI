package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 홈 화면의 카테고리별 상품 탭 섹션(HOME-001). FE 요청 009-home-card-response-fields 기준.
 *
 * <p><b>탭 구성은 카테고리 마스터(SY007)의 최상위 카테고리를 따른다</b> — 아우터·상의·하의·신발·
 * 가방·액세서리 6개다. FE 요청서에는 '원피스'가 있었으나 시드 데이터에 없는 카테고리라
 * 실제 마스터에 있는 '가방'으로 대체했다. 탭 목록을 화면에 하드코딩하지 말고 이 응답을 그대로
 * 그리면 마스터가 바뀌어도 FE 수정 없이 따라간다.
 */
public record CategoryProductSectionResponse(

        @Schema(description = "탭 식별자. 카테고리 ID를 문자열로 내린다", example = "10")
        String id,

        @Schema(description = "탭 버튼 표시명", example = "아우터")
        String title,

        @Schema(description = "카테고리명", example = "아우터")
        String categoryName,

        @Schema(description = "해당 카테고리 상품 목록")
        List<ProductCardResponse> products
) {
}