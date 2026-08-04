package com.ssafy.backend.auction.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

/**
 * 입찰(AUCT-003) 요청. 필드명은 FE 요청 {@code docs/requests/BE/009} §3.2를 그대로 따른다.
 *
 * <p><b>{@code amount}는 반드시 {@code GET .../auctions/current}가 내려준
 * {@code nextBidPrice}와 정확히 같아야 한다.</b> 그 이상·이하 모두 거부된다 — 서버가 계산해
 * 내려준 값을 클라이언트가 임의로 조정하면 "얼마를 불렀는지"가 불명확해진다.
 */
public record BidRequest(

        @Schema(
                description = "입찰 금액(원). `nextBidPrice`와 정확히 같아야 한다",
                example = "46000")
        @NotNull
        @PositiveOrZero
        Long amount
) {
}
