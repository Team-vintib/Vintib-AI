package com.ssafy.backend.live.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

/**
 * 라이브 상품 연결(LIVE-003) 요청.
 */
public record LiveProductLinkRequest(

        @Schema(description = "연결할 상품 ID", example = "2001")
        @NotNull
        Long productId,

        @Schema(description = "노출 순서. 생략하면 0", example = "0")
        @PositiveOrZero
        Short sortOrder
) {

    public short sortOrderOrDefault() {
        return sortOrder == null ? 0 : sortOrder;
    }
}
