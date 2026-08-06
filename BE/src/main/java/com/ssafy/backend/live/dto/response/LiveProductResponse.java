package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.port.ProductQueryPort.ProductCard;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * 라이브에 연결된 상품 응답(LIVE-003).
 *
 * <p>시청 화면 상품 패널이 이 응답만으로 그려져야 해서 상품 카드 필드를 함께 담는다
 * (FE 요청 {@code docs/requests/FE/006}). 상품 정보는 {@code ProductQueryPort}로만 가져온다 —
 * 라이브가 상품 리포지토리를 직접 잡지 않는다.
 */
public record LiveProductResponse(

        @Schema(description = "연결 ID", example = "5001")
        Long id,

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "상품 ID", example = "2001")
        Long productId,

        @Schema(description = "상품명", example = "리바이스 501 빈티지")
        String productTitle,

        @Schema(description = "브랜드명. 브랜드를 지정하지 않은 상품은 null", example = "Levi's")
        String brandName,

        @Schema(
                description = "가격(원). **경매 예정 상품은 아직 가격이 없어 null이다** — "
                        + "그 경우 FE는 가격 대신 '경매 예정'으로 표시한다",
                example = "45000")
        Long price,

        @Schema(
                description = "판매 방식. 아직 정해지지 않은 상품(DRAFT)은 null. "
                        + "**`FIXED_PRICE`가 아니라 `DIRECT_SALE`이다**",
                example = "AUCTION",
                allowableValues = {"DIRECT_SALE", "AUCTION"})
        String saleType,

        @Schema(
                description = "판매 상태. **`saleType`과는 별개 축이다** — 경매 상품도 팔리면 `SOLD`가 된다. "
                        + "상품 행을 찾지 못했거나 상태 미지정이면 null",
                example = "AUCTION_SCHEDULED",
                allowableValues = {
                        "DRAFT", "ON_SALE", "AUCTION_SCHEDULED", "AUCTION_IN_PROGRESS", "SOLD"})
        String saleStatus,

        @Schema(
                description = "중고 상태 등급. **등급 체계가 미확정이라 자유 문자열이다** — "
                        + "FE에서 enum으로 굳히지 말 것",
                example = "A")
        String conditionGrade,

        @Schema(description = "대표 이미지 URL. 등록된 이미지가 없으면 null")
        String thumbnailUrl,

        @Schema(description = "소재. 등록하지 않았으면 null", example = "코튼 100%")
        String material,

        @Schema(description = "실측 치수(cm). 항목이 상품마다 달라 키-값으로 내려간다. 없으면 null",
                example = "{\"어깨너비\": 45, \"총장\": 70}")
        Map<String, Integer> measurements,

        @Schema(
                description = "하자 요약. 등록된 하자 항목을 쉼표로 이어 붙인 한 줄 문자열. 없으면 null "
                        + "— 상세 목록이 필요하면 상품 상세(GET /api/products/{id})를 연다",
                example = "밑단 오염, 우측 소매 실밥 풀림")
        String defectSummary,

        @Schema(description = "노출 순서", example = "0")
        Short sortOrder,

        @Schema(description = "연결 시각", example = "2026-07-28T11:00:00")
        LocalDateTime addedAt
) {

    /**
     * @param card 상품 정보. <b>{@code null}이면 상품 행을 찾지 못한 경우</b>(삭제 등)이며 상품
     *             관련 필드가 전부 null이 된다. 연결 자체는 남아 있으므로 목록에서 빼지는 않는다 —
     *             호스트가 "왜 하나가 사라졌는지" 알 수 없게 되기 때문이다
     */
    public static LiveProductResponse of(LiveProduct liveProduct, ProductCard card) {
        return new LiveProductResponse(
                liveProduct.getId(),
                liveProduct.getLive().getId(),
                liveProduct.getProductId(),
                card == null ? null : card.title(),
                card == null ? null : card.brandName(),
                card == null ? null : card.price(),
                card == null ? null : card.saleType(),
                card == null ? null : card.saleStatus(),
                card == null ? null : card.conditionGrade(),
                card == null ? null : card.thumbnailUrl(),
                card == null ? null : card.material(),
                card == null ? null : card.measurements(),
                card == null ? null : card.defectSummary(),
                liveProduct.getSortOrder(),
                liveProduct.getAddedAt());
    }
}
