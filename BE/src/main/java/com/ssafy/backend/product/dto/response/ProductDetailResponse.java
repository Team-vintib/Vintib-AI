package com.ssafy.backend.product.dto.response;

import com.ssafy.backend.product.entity.AiModelGender;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.entity.SaleType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public record ProductDetailResponse(
        @Schema(example = "1") Long id,
        @Schema(example = "1") Long sellerId,
        @Schema(example = "vintagelover") String sellerNickname,
        @Schema(example = "1") Long categoryId,
        @Schema(example = "자켓") String categoryName,
        @Schema(example = "1") Long brandId,
        @Schema(example = "리바이스") String brandName,
        @Schema(example = "빈티지 리바이스 데님 자켓") String title,
        @Schema(example = "1990년대 리바이스 데님 자켓, 상태 양호") String description,
        @Schema(example = "A") String conditionGrade,
        @Schema(example = "M") String sizeLabel,
        @Schema(example = "블랙") String color,
        @Schema(example = "데님") String material,
        @Schema(example = "{\"총장\": 70, \"어깨너비\": 45}") Map<String, Integer> measurements,
        @Schema(example = "[\"소매 끝 실밥 풀림\"]") List<String> defects,
        @Schema(example = "DIRECT_SALE") SaleType saleType,
        @Schema(example = "ON_SALE") SaleStatus saleStatus,
        @Schema(example = "50000") Long price,
        List<ProductImageResponse> images,
        Boolean isWished,
        Long sellerFollowerCount,
        Long sellerProductCount,
        LinkedLiveSummaryResponse linkedLive,
        @Schema(description = "마네킹 사진 기반 AI 착용컷 사용 여부", example = "true") boolean aiModelEnabled,
        @Schema(description = "AI 착용컷 모델 성별. aiModelEnabled=false면 null", example = "FEMALE")
                AiModelGender aiModelGender,
        @Schema(description = "같은 카테고리 유사 상품 목록. 같은 브랜드 상품이 앞쪽에 온다")
                List<SimilarProductResponse> similarProducts,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime createdAt,
        @Schema(example = "2026-07-29T12:00:00") LocalDateTime updatedAt) {

    public static ProductDetailResponse from(
            Product product,
            String categoryName,
            String brandName,
            List<ProductImageResponse> images,
            List<String> defects,
            Boolean isWished,
            Long sellerFollowerCount,
            Long sellerProductCount,
            LinkedLiveSummaryResponse linkedLive,
            List<SimilarProductResponse> similarProducts) {
        return new ProductDetailResponse(
                product.getId(),
                product.getSeller().getId(),
                product.getSeller().getNickname(),
                product.getCategoryId(),
                categoryName,
                product.getBrandId(),
                brandName,
                product.getTitle(),
                product.getDescription(),
                product.getConditionGrade(),
                product.getSizeLabel(),
                product.getColor(),
                product.getMaterial(),
                product.getMeasurements(),
                defects,
                product.getSaleType(),
                product.getSaleStatus(),
                product.getPrice(),
                images,
                isWished,
                sellerFollowerCount,
                sellerProductCount,
                linkedLive,
                product.isAiModelEnabled(),
                product.getAiModelGender(),
                similarProducts,
                product.getCreatedAt(),
                product.getUpdatedAt());
    }
}
