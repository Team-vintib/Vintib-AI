package com.ssafy.backend.tryon.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record TryOnProfileResponse(
        @Schema(description = "전신 사진 presigned GET URL. 미등록이면 null", example = "https://s3.example.com/tryon-profiles/1/abc123.jpg?X-Amz-...")
        String bodyPhotoUrl,

        @Schema(example = "170") Short heightCm,
        @Schema(example = "60") Short weightKg,
        @Schema(example = "90") Short chest,
        @Schema(example = "70") Short waist,
        @Schema(example = "95") Short hip,
        @Schema(example = "2026-08-02T12:00:00") LocalDateTime updatedAt) {
}
