package com.ssafy.backend.product.dto.response;

public record ProductImageUploadUrlResponse(String key, String uploadUrl, long expiresInSeconds) {
}