package com.ssafy.backend.auction.dto.response;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 경매 결과 조회 응답(AUCT-012).
 *
 * <p><b>유찰도 200으로 답한다.</b> "낙찰자가 없다"는 오류가 아니라 결과의 한 종류다 — 404로
 * 돌려주면 FE 가 "경매가 없다"와 "안 팔렸다"를 구분할 수 없다. 유찰이면 {@code status}가
 * {@code FAILED}이고 낙찰자 관련 필드가 전부 {@code null}이다.
 */
public record AuctionWinnerResponse(

        @Schema(description = "경매 ID", example = "301")
        Long auctionId,

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "경매 상품 ID", example = "2001")
        Long productId,

        @Schema(
                description = "경매 결과. `SUCCESS`(낙찰) · `FAILED`(유찰). **아직 안 끝난 경매**"
                        + "(`READY`/`RUNNING`)도 그대로 내려주므로 종료 여부를 이 값으로 판단한다",
                example = "SUCCESS")
        AuctionStatus status,

        @Schema(description = "낙찰자 회원 ID. 유찰이거나 아직 진행 중이면 null", example = "7")
        Long winnerId,

        @Schema(description = "낙찰자 닉네임. 유찰이거나 아직 진행 중이면 null", example = "빈티지러버")
        String winnerNickname,

        @Schema(description = "낙찰가(원). 유찰이거나 아직 진행 중이면 null", example = "45000")
        Long finalPrice,

        @Schema(description = "총 입찰 횟수(밀린 입찰 포함)", example = "5")
        Long bidCount,

        @Schema(description = "실제 종료 시각. 아직 진행 중이면 null", example = "2026-08-05T21:41:05")
        LocalDateTime endedAt
) {

    /**
     * @param winnerNickname 낙찰자 닉네임. 유찰이면 {@code null}
     */
    public static AuctionWinnerResponse of(Auction auction, String winnerNickname, long bidCount) {
        return new AuctionWinnerResponse(
                auction.getId(),
                auction.getLive().getId(),
                auction.getProductId(),
                auction.getStatus(),
                auction.getWinnerId(),
                winnerNickname,
                auction.getFinalPrice(),
                bidCount,
                auction.getEndedAt());
    }
}
