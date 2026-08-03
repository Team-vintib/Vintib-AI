package com.ssafy.backend.order.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

public record OrderCreateRequest(

        @Schema(description = "구매할 상품 ID(상시 판매/ON_SALE 상태만 가능)", example = "10")
        @NotNull
        Long productId) {
}
