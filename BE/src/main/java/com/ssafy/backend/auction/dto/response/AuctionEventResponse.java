package com.ssafy.backend.auction.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 경매 실시간 이벤트 payload — {@code /topic/lives/{liveId}/auctions} (FE 요청 009 §3.3).
 *
 * <p><b>어떤 이벤트든 현황 전체를 함께 실어 보낸다.</b> 변화분만 보내면 프레임을 하나 놓친
 * 클라이언트가 영영 어긋난 상태로 남는다 — 경매는 초 단위로 바뀌는 화면이라 그 위험이 크다.
 * 매번 전체를 보내도 payload 가 수백 바이트라 비용이 문제되지 않는다.
 */
public record AuctionEventResponse(

        @Schema(
                description = "이벤트 종류. `AUCTION_STARTED`(시작) · `BID_PLACED`(입찰) · "
                        + "`AUCTION_CLOSED`(종료). **종료가 낙찰인지 유찰인지는 `auction.status`로 "
                        + "판단한다**(SUCCESS/FAILED)",
                example = "AUCTION_STARTED",
                allowableValues = {"AUCTION_STARTED", "BID_PLACED", "AUCTION_CLOSED"})
        AuctionEventType type,

        @Schema(description = "이벤트 시점의 경매 현황 전체")
        AuctionSnapshotResponse auction
) {

    public enum AuctionEventType {
        AUCTION_STARTED,
        BID_PLACED,
        AUCTION_CLOSED
    }

    public static AuctionEventResponse started(AuctionSnapshotResponse auction) {
        return new AuctionEventResponse(AuctionEventType.AUCTION_STARTED, auction);
    }

    public static AuctionEventResponse bidPlaced(AuctionSnapshotResponse auction) {
        return new AuctionEventResponse(AuctionEventType.BID_PLACED, auction);
    }

    public static AuctionEventResponse closed(AuctionSnapshotResponse auction) {
        return new AuctionEventResponse(AuctionEventType.AUCTION_CLOSED, auction);
    }
}
