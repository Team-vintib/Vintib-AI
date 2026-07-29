package com.ssafy.backend.wish.dto.response;

import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.wish.entity.Wish;
import java.time.LocalDateTime;

public record WishItemResponse(ProductResponse product, LocalDateTime wishedAt) {

    public static WishItemResponse of(Wish wish) {
        return new WishItemResponse(ProductResponse.from(wish.getProduct()), wish.getCreatedAt());
    }
}