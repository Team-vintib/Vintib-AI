package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 라이브 편성 상품이 정찰가로 팔렸음을 알리는 실시간 이벤트 — {@code /topic/lives/{liveId}/product-sold}
 * (JY013).
 *
 * <p><b>왜 별도 토픽인가.</b> 기존 {@code /topic/lives/{liveId}/product} 는 <b>현재 소개 중인
 * 상품</b>(NOW 배지)이고, {@code /auctions} 는 경매 스냅샷 모양이다. 정찰 판매를 둘 중 하나에
 * 실으면 FE 가 존재하지 않는 경매를 그리거나 NOW 배지를 잘못 옮긴다.
 *
 * <p><b>경매 낙찰은 여기로 오지 않는다.</b> 그건 {@code /auctions} 의 {@code AUCTION_CLOSED}
 * (status=SUCCESS)가 이미 알린다. 양쪽에서 쏘면 FE 가 같은 상품을 두 번 처리하게 된다.
 * {@code soldVia} 로 이 이벤트가 정찰 판매임을 명시한다.
 */
@Schema(description = "라이브 편성 상품 정찰 판매 이벤트")
public record LiveProductSoldResponse(

        @Schema(description = "이 상품이 편성된 진행 중 방송 ID", example = "101")
        Long liveId,

        @Schema(description = "팔린 상품 ID. FE 는 이 ID 로 상품 큐에서 찾아 상태를 바꾼다", example = "2001")
        Long productId,

        @Schema(
                description = "판매 후 상태. **항상 `SOLD`** 다 — 값을 고정해 두면 FE 가 분기 없이 "
                        + "그대로 대입할 수 있다",
                example = "SOLD",
                allowableValues = {"SOLD"})
        String saleStatus,

        @Schema(
                description = "판매 경로. 이 토픽은 정찰 판매 전용이라 **항상 `DIRECT_SALE`** 이다. "
                        + "경매 낙찰은 `/topic/lives/{liveId}/auctions` 로 간다",
                example = "DIRECT_SALE",
                allowableValues = {"DIRECT_SALE"})
        String soldVia,

        @Schema(description = "판매 시각(서버 시각)", example = "2026-08-07T14:20:31")
        LocalDateTime soldAt
) {

    private static final String SOLD = "SOLD";
    private static final String DIRECT_SALE = "DIRECT_SALE";

    public static LiveProductSoldResponse directSale(Long liveId, Long productId, LocalDateTime soldAt) {
        return new LiveProductSoldResponse(liveId, productId, SOLD, DIRECT_SALE, soldAt);
    }
}
