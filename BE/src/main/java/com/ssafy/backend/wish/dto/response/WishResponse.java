package com.ssafy.backend.wish.dto.response;

import com.ssafy.backend.wish.entity.Wish;
import java.time.LocalDateTime;

public record WishResponse(Long productId, LocalDateTime createdAt) {

    public static WishResponse of(Wish wish) {
        return new WishResponse(wish.getProduct().getId(), wish.getCreatedAt());
    }
}
