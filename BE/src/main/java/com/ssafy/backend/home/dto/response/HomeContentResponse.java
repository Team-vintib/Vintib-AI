package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 홈 콘텐츠 조회(HOME-001) 응답. 섹션별 목록으로 구성한다.
 */
public record HomeContentResponse(

        @Schema(description = "진행 중 라이브")
        List<LiveCardResponse> liveNow,

        @Schema(description = "예약 라이브")
        List<LiveCardResponse> scheduledLives,

        @Schema(description = "상시 판매 상품")
        List<ProductCardResponse> onSaleProducts,

        @Schema(description = "경매 예정 상품")
        List<ProductCardResponse> upcomingAuctionProducts
) {
}