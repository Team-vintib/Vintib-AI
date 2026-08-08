package com.ssafy.backend.product.port.dto;

import lombok.Builder;

/** 상품 하나의 완료거래 요약("동일 상품 시세", CH001). {@code auctionWin}으로 직접판매/경매낙찰을 구분한다. */
@Builder
public record CompletedOrderSummary(
    Long productId,
    Long orderPrice,
    boolean auctionWin
) {
}
