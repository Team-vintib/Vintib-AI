package com.ssafy.backend.auction.dto.response;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 경매 현황 한 장(AUCT-002). 라이브 진입 시 경매 패널을 이 응답 하나로 초기화하고,
 * 이후 변화는 {@code /topic/lives/{liveId}/auctions} 구독으로 받는다.
 *
 * <p><b>같은 타입이 REST 응답과 STOMP payload 양쪽에 쓰인다.</b> 초기화와 갱신이 다른 모양이면
 * FE가 화면 상태를 두 가지 경로로 조립해야 하고, 필드가 하나 늘 때마다 두 곳이 어긋난다.
 *
 * <p><b>{@code serverNow}를 함께 내리는 이유.</b> 남은 시간을 그리려면 종료 시각만으로는 부족하다 —
 * 클라이언트 시계가 서버와 몇 초씩 어긋나는 것이 정상이라, FE는 {@code endsAt - serverNow}로
 * 남은 시간을 구하고 그 뒤로는 자기 시계로 세야 한다. 서버 시각을 안 주면 카운트다운이 0이
 * 됐는데 서버는 아직 진행 중인 구간이 생긴다.
 */
public record AuctionSnapshotResponse(

        @Schema(description = "경매 ID", example = "301")
        Long auctionId,

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "경매 상품 ID", example = "2001")
        Long productId,

        @Schema(description = "상품명. 상품을 찾지 못하면 null", example = "리바이스 501 빈티지")
        String productTitle,

        @Schema(
                description = "경매 상태. `READY`(시작 전) · `RUNNING`(진행 중) · `SUCCESS`(낙찰) · "
                        + "`FAILED`(유찰) · `CANCELED`. **종료는 SUCCESS/FAILED로 나뉜다** — "
                        + "낙찰 축하 연출은 SUCCESS일 때만 띄운다",
                example = "RUNNING")
        AuctionStatus status,

        @Schema(description = "시작가(원)", example = "10000")
        Long startPrice,

        @Schema(description = "증액 단위(원)", example = "1000")
        Long bidUnit,

        @Schema(description = "진행 시간(초). 연장은 별개로 endsAt에 반영된다", example = "60")
        Integer durationSeconds,

        @Schema(description = "현재가(원). **입찰이 없으면 0이다**(시작가가 아니다)", example = "45000")
        Long currentPrice,

        @Schema(
                description = "다음에 넣어야 하는 최소 입찰가(원). **첫 입찰은 시작가 그대로**이고 "
                        + "그 뒤로는 현재가 + 증액 단위다. FE 입찰 버튼은 이 값을 그대로 보내면 된다 — "
                        + "클라이언트가 같은 계산을 다시 하면 정책이 바뀔 때 어긋난다",
                example = "46000")
        Long nextBidPrice,

        @Schema(description = "최고 입찰자 회원 ID. 입찰이 없으면 null", example = "7")
        Long highestBidderId,

        @Schema(description = "최고 입찰자 닉네임. 입찰이 없으면 null", example = "빈티지러버")
        String highestBidderNickname,

        @Schema(description = "총 입찰 횟수(밀린 입찰 포함)", example = "5")
        Long bidCount,

        @Schema(description = "경매 시작 시각. 아직 시작 전이면 null", example = "2026-08-03T21:40:00")
        LocalDateTime startedAt,

        @Schema(
                description = "종료 예정 시각. 시작 전이면 null. **마감 직전 입찰이 들어오면 뒤로 밀린다**"
                        + "(AUCT-010) — 이 값이 바뀌면 카운트다운을 다시 맞춰야 한다",
                example = "2026-08-03T21:41:00")
        LocalDateTime endsAt,

        @Schema(description = "실제 종료 시각. 진행 중이면 null", example = "2026-08-03T21:41:05")
        LocalDateTime endedAt,

        @Schema(description = "연장 횟수", example = "2")
        Short extensionCount,

        @Schema(
                description = "**응답을 만든 시각(서버 기준).** 남은 시간은 `endsAt - serverNow`로 "
                        + "계산한다 — 클라이언트 시계를 그대로 쓰면 카운트다운이 서버와 어긋난다",
                example = "2026-08-03T21:40:30")
        LocalDateTime serverNow
) {

    /**
     * @param productTitle  상품명. 상품 행을 찾지 못하면 {@code null}
     * @param bidderNickname 최고 입찰자 닉네임. 입찰이 없으면 {@code null}
     */
    public static AuctionSnapshotResponse of(
            Auction auction, String productTitle, String bidderNickname, long bidCount, LocalDateTime serverNow) {
        return new AuctionSnapshotResponse(
                auction.getId(),
                auction.getLive().getId(),
                auction.getProductId(),
                productTitle,
                auction.getStatus(),
                auction.getStartPrice(),
                auction.getBidUnit(),
                auction.getDurationSeconds(),
                auction.getCurrentPrice(),
                auction.nextBidPrice(),
                auction.getTopBidderId(),
                bidderNickname,
                bidCount,
                auction.getStartedAt(),
                auction.getScheduledEndAt(),
                auction.getEndedAt(),
                auction.getExtensionCount(),
                serverNow);
    }
}
