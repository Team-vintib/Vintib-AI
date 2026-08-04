package com.ssafy.backend.auction.dto.response;

import com.ssafy.backend.auction.entity.Bid;
import com.ssafy.backend.auction.entity.BidStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/** 입찰 내역 한 건(AUCT-003) — {@code GET /api/auctions/{auctionId}/bids} 커서 페이징 항목. */
public record BidResponse(

        @Schema(description = "입찰 ID", example = "5001")
        Long bidId,

        @Schema(description = "입찰자 회원 ID", example = "7")
        Long bidderId,

        @Schema(description = "입찰자 닉네임", example = "빈티지러버")
        String bidderNickname,

        @Schema(description = "입찰 금액(원)", example = "46000")
        Long amount,

        @Schema(
                description = "입찰 상태. `ACTIVE`(현재 최고) · `OUTBID`(상위 입찰에 밀림) · "
                        + "`WON`(낙찰) · `LOST`(낙찰 실패)",
                example = "OUTBID")
        BidStatus status,

        @Schema(description = "입찰 시각(서버 수신 기준)", example = "2026-08-04T21:40:12")
        LocalDateTime createdAt,

        @Schema(description = "요청한 회원 본인의 입찰인지. 비회원이면 항상 false", example = "false")
        boolean isMine
) {

    public static BidResponse of(Bid bid, Long viewerId) {
        return new BidResponse(
                bid.getId(),
                bid.getBidder().getId(),
                bid.getBidder().getNickname(),
                bid.getBidPrice(),
                bid.getStatus(),
                bid.getCreatedAt(),
                viewerId != null && viewerId.equals(bid.getBidder().getId()));
    }
}
