package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import java.time.LocalDateTime;
import java.util.List;

public record ProductDetailResponse(
        Long id,
        Long sellerId,
        String sellerNickname,
        Long categoryId,
        Long brandId,
        String title,
        String description,
        String conditionGrade,
        String sizeLabel,
        SaleType saleType,
        SaleStatus saleStatus,
        Long price,
        List<ProductImageResponse> images,
        LocalDateTime createdAt,
        LocalDateTime updatedAt) {

    public static ProductDetailResponse from(Product product, List<ProductImageResponse> images) {
        return new ProductDetailResponse(
                product.getId(),
                product.getSeller().getId(),
                product.getSeller().getNickname(),
                product.getCategoryId(),
                product.getBrandId(),
                product.getTitle(),
                product.getDescription(),
                product.getConditionGrade(),
                product.getSizeLabel(),
                product.getSaleType(),
                product.getSaleStatus(),
                product.getPrice(),
                images,
                product.getCreatedAt(),
                product.getUpdatedAt());
    }
}
