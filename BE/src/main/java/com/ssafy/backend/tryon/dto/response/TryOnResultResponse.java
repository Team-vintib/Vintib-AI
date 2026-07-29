package com.ssafy.backend.tryon.dto.response;

import com.ssafy.backend.tryon.entity.TryOnResult;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record TryOnResultResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "1") Long productId,
        @Schema(example = "https://s3.example.com/tryon-results/1/abc123.jpg?X-Amz-...") String imageUrl,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt) {

    public static TryOnResultResponse of(TryOnResult result, String imageUrl) {
        return new TryOnResultResponse(
                result.getId(), result.getProduct().getId(), imageUrl, result.getCreatedAt());
    }
}