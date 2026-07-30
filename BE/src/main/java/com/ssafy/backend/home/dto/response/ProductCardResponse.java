package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 홈/팔로잉 화면의 상품 카드 공통 응답. (HOME-001 소유, HOME-002 재사용)
 *
 * <p>판매 방식({@code sellType})과 판매 상태({@code sellStatus})는 방송 상태와 구분되는 별도 축이다
 * (기능정의서 HOME-001 정책). 경매 예정 상품은 아직 가격이 없어 {@code price}가 null이며,
 * {@code auctionScheduled=true}로 내려 FE가 가격 대신 '경매 예정'으로 표시하게 한다.
 * 2주차에 상품 도메인(서윤) 엔티티가 준비되면 그 상태 enum → 여기 문자열로 매핑한다.
 */
public record ProductCardResponse(

        @Schema(description = "상품 ID", example = "2001")
        Long productId,

        @Schema(description = "상품명", example = "리바이스 501 빈티지")
        String name,

        @Schema(description = "브랜드", example = "Levi's")
        String brand,

        @Schema(description = "썸네일 URL", example = "https://picsum.photos/seed/product2001/480/480")
        String thumbnailUrl,

        @Schema(description = "판매 방식", example = "NORMAL", allowableValues = {"NORMAL", "AUCTION_SCHEDULED"})
        String sellType,

        @Schema(description = "판매 상태", example = "ON_SALE", allowableValues = {"ON_SALE", "RESERVED", "SOLD_OUT"})
        String sellStatus,

        @Schema(description = "가격(원). 경매 예정 상품은 가격이 없어 null", example = "45000")
        Long price,

        @Schema(description = "경매 예정 여부. true면 FE는 가격 대신 '경매 예정'으로 표시한다", example = "false")
        boolean auctionScheduled,

        @Schema(description = "판매자 표시명", example = "빈티지장인")
        String sellerName,

        @Schema(description = "카테고리명. 미분류 상품은 null", example = "하의")
        String categoryName,

        @Schema(
                description = "회원별 찜 여부. **비회원 요청이면 null**이며, FE는 이 경우 찜 아이콘을 비활성 상태로 둔다",
                example = "false")
        Boolean isWished,

        @Schema(description = "경매 시작가(원). 경매 예정 상품만 값을 갖는다", example = "50000")
        Long startingBid,

        @Schema(description = "경매 시작 예정 시각. 경매 예정 상품만 값을 갖는다", example = "2026-08-01T20:00:00")
        LocalDateTime auctionStartsAt
) {
}