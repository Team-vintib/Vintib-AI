package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record ProductPreUploadUrlResponse(
        @Schema(example = "pre-upload/7/3f2a9c1e-....jpg") String key,
        @Schema(example = "https://s3.example.com/pre-upload/7/3f2a9c1e-....jpg?X-Amz-...") String uploadUrl,
        @Schema(example = "300") long expiresInSeconds) {
}
