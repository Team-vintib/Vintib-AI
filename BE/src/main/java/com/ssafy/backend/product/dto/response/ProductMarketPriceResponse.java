package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * "동일 상품 시세"(CH001, 047·025) 응답. {@code matchKey}가 아직 없는 상품이면 {@code matchKey}가
 * null이고 {@code listings}가 빈 배열이다(404가 아니다 — 판정 근거가 없을 뿐 정상 응답).
 */
public record ProductMarketPriceResponse(
        @Schema(example = "42") Long productId,
        @Schema(description = "동일 상품 판정 키. 아직 계산되지 않았으면 null", example = "1:501-리바이스:97")
        String matchKey,
        @Schema(description = "이 상품 자신의 현재가. 아직 가격/판매 상태가 확정되지 않았으면 null")
        Item currentProduct,
        @Schema(description = "같은 matchKey를 가진 다른 상품들(호가+완료거래)")
        List<Item> listings) {

    public record Item(
            @Schema(example = "17") Long productId,
            @Schema(example = "리바이스 501 빈티지") String title,
            @Schema(example = "45000") Long price,
            @Schema(description = "ASKING(호가) | SOLD_DIRECT(직접판매 완료) | SOLD_AUCTION(경매 낙찰)", example = "SOLD_DIRECT")
            String priceKind) {
    }
}
