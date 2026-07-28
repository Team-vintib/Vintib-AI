package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.LiveProduct;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 라이브에 연결된 상품 응답(LIVE-003).
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

        @Schema(description = "노출 순서", example = "0")
        Short sortOrder,

        @Schema(description = "연결 시각", example = "2026-07-28T11:00:00")
        LocalDateTime addedAt
) {

    public static LiveProductResponse of(LiveProduct liveProduct, String productTitle) {
        return new LiveProductResponse(
                liveProduct.getId(),
                liveProduct.getLive().getId(),
                liveProduct.getProductId(),
                productTitle,
                liveProduct.getSortOrder(),
                liveProduct.getAddedAt());
    }
}
