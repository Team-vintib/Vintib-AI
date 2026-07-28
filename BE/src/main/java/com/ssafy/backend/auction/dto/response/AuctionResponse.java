package com.ssafy.backend.auction.dto.response;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 경매 응답. 이번 단계(AUCT-001)에서는 조건과 상태만 채워지고, 진행 관련 값은
 * 경매 시작·입찰(AUCT-002 이후)에서 갱신된다.
 */
public record AuctionResponse(

        @Schema(description = "경매 ID", example = "301")
        Long id,

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "상품 ID", example = "2001")
        Long productId,

        @Schema(description = "시작가(원)", example = "10000")
        Long startPrice,

        @Schema(description = "증액 단위(원)", example = "1000")
        Long bidUnit,

        @Schema(description = "진행 시간(초)", example = "60")
        Integer durationSeconds,

        @Schema(description = "경매 상태", example = "READY")
        AuctionStatus status,

        @Schema(description = "현재가(원). 입찰이 없으면 0", example = "0")
        Long currentPrice,

        @Schema(description = "생성 시각", example = "2026-07-28T13:00:00")
        LocalDateTime createdAt
) {

    public static AuctionResponse from(Auction auction) {
        return new AuctionResponse(
                auction.getId(),
                auction.getLive().getId(),
                auction.getProductId(),
                auction.getStartPrice(),
                auction.getBidUnit(),
                auction.getDurationSeconds(),
                auction.getStatus(),
                auction.getCurrentPrice(),
                auction.getCreatedAt());
    }
}