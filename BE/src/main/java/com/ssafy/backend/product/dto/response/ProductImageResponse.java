package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.ProductImage;

public record ProductImageResponse(Long id, String url, Short sortOrder, boolean isPrimary) {

    public static ProductImageResponse of(ProductImage image, String url) {
        return new ProductImageResponse(image.getId(), url, image.getSortOrder(), image.isPrimary());
    }
}