package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import io.swagger.v3.oas.annotations.media.Schema;

public record SimilarProductResponse(
        @Schema(example = "12") Long id,
        @Schema(example = "Maison Kitsuné 더블 폭스 헤드 패치 폴로 반팔 셔츠 블랙") String title,
        @Schema(example = "65000") Long price) {

    public static SimilarProductResponse from(Product product) {
        return new SimilarProductResponse(product.getId(), product.getTitle(), product.getPrice());
    }
}
