package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Brand;
import io.swagger.v3.oas.annotations.media.Schema;

public record BrandResponse(

        @Schema(example = "1") Long id,
        @Schema(example = "Maison Kitsuné") String name,
        @Schema(example = "Maison Kitsuné") String nameEn) {

    public static BrandResponse from(Brand brand) {
        return new BrandResponse(brand.getId(), brand.getName(), brand.getNameEn());
    }
}
