package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import java.util.List;

public record ProductDetailResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "1") Long sellerId,
        @Schema(example = "vintagelover") String sellerNickname,
        @Schema(example = "1") Long categoryId,
        @Schema(example = "1") Long brandId,
        @Schema(example = "빈티지 리바이스 데님 자켓") String title,
        @Schema(example = "1990년대 리바이스 데님 자켓, 상태 양호") String description,
        @Schema(example = "A") String conditionGrade,
        @Schema(example = "M") String sizeLabel,
        @Schema(example = "DIRECT_SALE") SaleType saleType,
        @Schema(example = "ON_SALE") SaleStatus saleStatus,
        @Schema(example = "50000") Long price,
        List<ProductImageResponse> images,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime updatedAt) {

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
