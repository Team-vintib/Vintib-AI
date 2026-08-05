package com.ssafy.backend.auction.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 방송 종료 요약(FE 요청 018, 판매자 방송 종료 대시보드).
 *
 * <p><b>경매 낙찰과 방송 중 즉시구매를 함께 센다.</b> 방송 실적이지 경매 실적이 아니므로 정찰가로
 * 팔린 것도 들어가야 한다. 즉시구매는 주문만 봐서는 어느 방송에서 팔렸는지 알 수 없어
 * {@code orders.live_id}로 잇는다 — FE 가 라이브 구매 요청에 {@code liveId}를 실어야 잡힌다.
 * 어느 경로로 팔렸는지는 {@link Result#soldVia}로 구분한다.
 *
 * <p>{@code results}는 <b>편성 상품 전체</b>가 기준이다 — 경매를 걸지 않은 상품도 UNSOLD 로
 * 나와야 대시보드가 방송 전체를 보여 준다.
 */
public record LiveBroadcastSummaryResponse(

        @Schema(description = "판매된 상품 수(낙찰 + 방송 중 즉시구매)", example = "3")
        int soldCount,

        @Schema(description = "판매되지 않은 상품 수. 경매를 걸지 않은 편성 상품도 포함한다", example = "2")
        int unsoldCount,

        @Schema(description = "총 판매액(원). 낙찰가와 즉시구매가의 합계다", example = "452000")
        long totalSales,

        @Schema(description = "편성 상품별 결과. 편성 순서를 그대로 따른다")
        List<Result> results
) {

    /** 편성 상품 한 건의 방송 결과. */
    public record Result(

            @Schema(description = "상품 ID", example = "2001")
            Long productId,

            @Schema(description = "상품명", example = "리바이스 501 빈티지")
            String title,

            @Schema(description = "대표 이미지 URL. 등록된 이미지가 없으면 null")
            String thumbnailUrl,

            @Schema(
                    description = "판매 여부. `SOLD`(팔림) / `UNSOLD`(안 팔림). "
                            + "**경매를 걸지 않은 편성 상품도 `UNSOLD`다**",
                    example = "SOLD",
                    allowableValues = {"SOLD", "UNSOLD"})
            String status,

            @Schema(description = "낙찰가(원). 안 팔렸으면 null", example = "89000")
            Long finalPrice,

            @Schema(
                    description = "판매 경로. `AUCTION`(경매 낙찰) / `DIRECT_SALE`(방송 중 정찰가 즉시구매). "
                            + "안 팔렸으면 null",
                    example = "AUCTION",
                    allowableValues = {"AUCTION", "DIRECT_SALE"})
            String soldVia
    ) {

        private static final String SOLD = "SOLD";
        private static final String UNSOLD = "UNSOLD";
        private static final String VIA_AUCTION = "AUCTION";
        private static final String VIA_DIRECT_SALE = "DIRECT_SALE";

        /** 경매 낙찰로 팔렸다. */
        public static Result wonAtAuction(Long productId, String title, String thumbnailUrl, Long finalPrice) {
            return new Result(productId, title, thumbnailUrl, SOLD, finalPrice, VIA_AUCTION);
        }

        /** 방송 중 정찰가로 팔렸다(경매를 거치지 않음). */
        public static Result soldDirectly(Long productId, String title, String thumbnailUrl, Long orderPrice) {
            return new Result(productId, title, thumbnailUrl, SOLD, orderPrice, VIA_DIRECT_SALE);
        }

        public static Result unsold(Long productId, String title, String thumbnailUrl) {
            return new Result(productId, title, thumbnailUrl, UNSOLD, null, null);
        }

        public boolean isSold() {
            return SOLD.equals(status);
        }
    }
}
