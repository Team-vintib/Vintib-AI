package com.ssafy.backend.tryon.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record TryOnProfileUploadUrlResponse(
        @Schema(example = "tryon-profiles/1/abc123.jpg") String key,
        @Schema(example = "https://s3.example.com/tryon-profiles/1/abc123.jpg?X-Amz-...") String uploadUrl,
        @Schema(example = "300") long expiresInSeconds) {
}
