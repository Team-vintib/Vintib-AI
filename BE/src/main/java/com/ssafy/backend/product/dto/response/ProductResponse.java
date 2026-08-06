package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

public record ProductResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "1") Long sellerId,
        @Schema(example = "1") Long categoryId,
        @Schema(example = "1") Long brandId,
        @Schema(example = "Maison Kitsuné 더블 폭스 헤드 패치 클래식 티셔츠 블랙") String title,
        @Schema(example = "시착 0회. 더블 폭스 헤드 자수 패치. Maison Kitsuné Paris 정품.") String description,
        @Schema(example = "A") String conditionGrade,
        @Schema(example = "M") String sizeLabel,
        @Schema(example = "DIRECT_SALE") SaleType saleType,
        @Schema(example = "ON_SALE") SaleStatus saleStatus,
        @Schema(example = "85000") Long price,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt,
        @Schema(description = "대표 이미지 URL. 등록된 이미지가 없으면 null") String primaryImageUrl) {

    public static ProductResponse from(Product product) {
        return from(product, null);
    }

    public static ProductResponse from(Product product, String primaryImageUrl) {
        return new ProductResponse(
                product.getId(),
                product.getSeller().getId(),
                product.getCategoryId(),
                product.getBrandId(),
                product.getTitle(),
                product.getDescription(),
                product.getConditionGrade(),
                product.getSizeLabel(),
                product.getSaleType(),
                product.getSaleStatus(),
                product.getPrice(),
                product.getCreatedAt(),
                primaryImageUrl);
    }
}
