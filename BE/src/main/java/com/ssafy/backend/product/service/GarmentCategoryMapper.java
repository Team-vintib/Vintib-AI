package com.ssafy.backend.product.service;

import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.Map;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * BE 카테고리(leaf, {@link Category#getNameEn()}) → AI SAM3/가격책정 공용
 * {@code GarmentCategory}(6종, {@code worker/models/sam3/contracts.py}) 매핑.
 *
 * <p>하자 검수({@code ProductImageService})와 가격 추천 트리거({@code PriceEstimateService})
 * 가 같은 매핑을 공유한다 — 둘 다 AI 쪽 같은 6종 enum을 받는다.
 *
 * <p>SAM3는 의류(상/하의·아우터) 전용이라 신발/가방/액세서리/원피스·점프슈트는 대응값이 없다 —
 * 이 맵에 없으면 {@link #resolve} 결과가 비어있고, 호출부는 그 상황에 맞게(하자 검수는 건너뛰기,
 * 가격 추천은 category 없이 진행) 처리한다.
 *
 * <p>⚠️ 라벨링된 기준 없이 잡은 매핑(특히 TSHIRT/SLEEVELESS→TOP_SHIRT, HOODIE/SWEATSHIRT→
 * TOP_KNIT, JACKET/CARDIGAN/HOOD_ZIPUP→OUTER_JACKET, COAT/PADDED_JACKET→OUTER_COAT 경계는
 * 판단 근거가 약하다) — AI/BE가 함께 다시 검토할 대상.
 */
@Component
@RequiredArgsConstructor
public class GarmentCategoryMapper {

    private static final Map<String, String> GARMENT_CATEGORY_BY_LEAF_NAME = Map.ofEntries(
            Map.entry("TSHIRT", "TOP_SHIRT"),
            Map.entry("SHIRT", "TOP_SHIRT"),
            Map.entry("SLEEVELESS", "TOP_SHIRT"),
            Map.entry("KNIT", "TOP_KNIT"),
            Map.entry("HOODIE", "TOP_KNIT"),
            Map.entry("SWEATSHIRT", "TOP_KNIT"),
            Map.entry("JACKET", "OUTER_JACKET"),
            Map.entry("CARDIGAN", "OUTER_JACKET"),
            Map.entry("HOOD_ZIPUP", "OUTER_JACKET"),
            Map.entry("COAT", "OUTER_COAT"),
            Map.entry("PADDED_JACKET", "OUTER_COAT"),
            Map.entry("DENIM", "BOTTOM_PANTS"),
            Map.entry("SLACKS", "BOTTOM_PANTS"),
            Map.entry("CARGO_PANTS", "BOTTOM_PANTS"),
            Map.entry("SHORT_PANTS", "BOTTOM_PANTS"),
            Map.entry("JOGGER_PANTS", "BOTTOM_PANTS"),
            Map.entry("COTTON_PANTS", "BOTTOM_PANTS"),
            Map.entry("SKIRT", "BOTTOM_SKIRT"));

    private final CategoryRepository categoryRepository;

    /** {@code categoryId}가 없거나 존재하지 않거나 매핑이 없으면 빈 값. */
    public Optional<String> resolve(Long categoryId) {
        if (categoryId == null) {
            return Optional.empty();
        }
        return categoryRepository.findById(categoryId)
                .map(Category::getNameEn)
                .map(GARMENT_CATEGORY_BY_LEAF_NAME::get);
    }
}