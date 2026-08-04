package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import io.swagger.v3.oas.annotations.media.Schema;

public record SimilarProductResponse(
        @Schema(example = "12") Long id,
        @Schema(example = "빈티지 데님 자켓") String title,
        @Schema(example = "89000") Long price) {

    public static SimilarProductResponse from(Product product) {
        return new SimilarProductResponse(product.getId(), product.getTitle(), product.getPrice());
    }
}
