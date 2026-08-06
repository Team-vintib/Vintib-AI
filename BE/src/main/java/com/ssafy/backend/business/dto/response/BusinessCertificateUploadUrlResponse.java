package com.ssafy.backend.business.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

public record BusinessCertificateUploadUrlResponse(
        @Schema(example = "business-certificates/1/abc123.jpg") String key,
        @Schema(example = "https://s3.example.com/business-certificates/1/abc123.jpg?X-Amz-...") String uploadUrl,
        @Schema(example = "300") long expiresInSeconds) {
}