package com.ssafy.backend.auction.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 방송별 유찰 상품 한 건(LIVE-006, FE `-440` 미낙찰 상품 처리).
 *
 * <p>판매자가 다음 행동(정찰제 전환 / 그대로 두고 재경매)을 고를 수 있을 만큼만 담는다 —
 * 상품 상세가 필요하면 {@code GET /api/products/{id}}를 연다.
 */
public record LiveUnsoldProductResponse(

        @Schema(description = "상품 ID", example = "2001")
        Long productId,

        @Schema(description = "상품명", example = "리바이스 501 빈티지")
        String title,

        @Schema(description = "대표 이미지 URL. 등록된 이미지가 없으면 null")
        String thumbnailUrl,

        @Schema(
                description = "이 방송에서 마지막으로 걸었던 경매의 시작가(원). 재경매 시 기본값으로 쓰면 된다",
                example = "10000")
        Long startPrice
) {
}
