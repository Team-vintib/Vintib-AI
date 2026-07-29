package com.ssafy.backend.social.dto.response;

import com.ssafy.backend.social.entity.Wish;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record WishResponse(
        @Schema(example = "1") Long productId,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt) {

    public static WishResponse of(Wish wish) {
        return new WishResponse(wish.getProduct().getId(), wish.getCreatedAt());
    }
}
