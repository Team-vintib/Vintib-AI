package com.ssafy.backend.auction.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

/**
 * 경매 조건 설정(AUCT-001) 요청.
 *
 * <p>금액은 원 단위 정수다(KRW는 소수점이 없다 — erd.md §6). 시작가만 0을 허용하고
 * 증액 단위·진행 시간은 0이면 경매가 성립하지 않으므로 양수만 받는다. 같은 제약이
 * DB에도 `ck_auction_bid_unit`, `ck_auction_start_price`로 걸려 있다.
 */
public record AuctionConfigRequest(

        @Schema(description = "경매에 걸 상품 ID. 해당 라이브에 연결된 상품이어야 한다", example = "2001")
        @NotNull
        Long productId,

        @Schema(description = "시작가(원)", example = "10000")
        @NotNull
        @PositiveOrZero
        Long startPrice,

        @Schema(description = "증액 단위(원)", example = "1000")
        @NotNull
        @Positive
        Long bidUnit,

        @Schema(description = "진행 시간(초)", example = "60")
        @NotNull
        @Positive
        Integer durationSeconds
) {
}