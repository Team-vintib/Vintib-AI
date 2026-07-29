package com.ssafy.backend.social.dto.response;

import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.social.entity.Wish;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record WishItemResponse(
        ProductResponse product,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime wishedAt) {

    public static WishItemResponse of(Wish wish) {
        return new WishItemResponse(ProductResponse.from(wish.getProduct()), wish.getCreatedAt());
    }
}