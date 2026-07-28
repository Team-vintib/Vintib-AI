package com.ssafy.backend.tryon.dto.response;

import com.ssafy.backend.tryon.entity.TryOnResult;
import java.time.LocalDateTime;

public record TryOnResultResponse(Long id, Long productId, String imageUrl, LocalDateTime createdAt) {

    public static TryOnResultResponse of(TryOnResult result, String imageUrl) {
        return new TryOnResultResponse(
                result.getId(), result.getProduct().getId(), imageUrl, result.getCreatedAt());
    }
}