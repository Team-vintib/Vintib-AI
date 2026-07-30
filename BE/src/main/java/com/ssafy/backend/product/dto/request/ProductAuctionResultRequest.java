package com.ssafy.backend.product.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record ProductAuctionResultRequest(

        @Schema(example = "ON_SALE") @NotNull NextStatus nextStatus,

        @Schema(example = "50000") @Positive Long price) {

    public enum NextStatus {
        ON_SALE,
        AUCTION_SCHEDULED
    }
}
