package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Brand;

public record BrandResponse(Long id, String name, String nameEn) {

    public static BrandResponse from(Brand brand) {
        return new BrandResponse(brand.getId(), brand.getName(), brand.getNameEn());
    }
}
