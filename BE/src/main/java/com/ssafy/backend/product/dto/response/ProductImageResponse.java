package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.ProductImage;
import com.ssafy.backend.product.entity.ProductImageRole;
import io.swagger.v3.oas.annotations.media.Schema;

public record ProductImageResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "https://s3.example.com/product-images/1/abc123.jpg") String url,
        @Schema(example = "0") Short sortOrder,
        @Schema(example = "true") boolean isPrimary,
        @Schema(example = "FRONT") ProductImageRole role) {

    public static ProductImageResponse of(ProductImage image, String url) {
        return new ProductImageResponse(
                image.getId(), url, image.getSortOrder(), image.isPrimary(), image.getRole());
    }
}
