package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 홈 콘텐츠 조회(HOME-001) 응답. 섹션별 목록으로 구성한다.
 *
 * <p>모든 섹션은 빈 배열을 허용한다 — FE는 빈 섹션을 숨기거나 empty 상태로 처리한다.
 * 하단 배너·콘텐츠 카드 섹션은 FE 화면에서 제거돼 응답에 두지 않는다
 * (FE 요청 009-home-card-response-fields 요청 8).
 */
public record HomeContentResponse(

        @Schema(description = "진행 중 라이브")
        List<LiveCardResponse> liveNow,

        @Schema(description = "예약 라이브")
        List<LiveCardResponse> scheduledLives,

        @Schema(description = "정찰제 상품")
        List<ProductCardResponse> onSaleProducts,

        @Schema(description = "경매 예정 상품")
        List<ProductCardResponse> upcomingAuctionProducts,

        @Schema(description = "카테고리별 상품 탭 섹션. 카테고리 마스터의 최상위 카테고리를 따른다")
        List<CategoryProductSectionResponse> categoryProductSections
) {
}