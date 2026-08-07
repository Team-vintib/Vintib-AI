package com.ssafy.backend.product.support;

import java.util.Map;

/**
 * AI 분류 소분류 코드(예: "CARDIGAN") -> BE categoryId(depth2/depth3) 정적 조회표.
 * `docs/requests/BE/045-classify-pre-upload-integration.md`에 실린 표(AI
 * {@code worker/models/product_classifier/taxonomy.py::CATEGORY_ID_MAP}을 BE 시드 기준으로
 * 옮긴 것)를 그대로 하드코딩한다 — {@code ProductImageService.GARMENT_CATEGORY_BY_LEAF_NAME}과
 * 같은 관례(DB 조회 없는 정적 Map).
 *
 * <p>사전업로드 트리거 시점엔 판매자가 아직 성별을 고르지 않았을 수 있어 <b>남성 기준을
 * 우선</b>하고, 남성에 없는 소분류(DRESS/JUMPSUIT)만 여성 기준으로 폴백한다 — UNISEX가
 * 아니다. FE 카테고리 드롭다운이 같은 한글 라벨의 성별별 옵션 중 categoryId가 가장 낮은
 * 것(=남성)만 남기고 나머지는 중복 제거하기 때문에, UNISEX id를 주면 대부분의 소분류에서
 * 드롭다운에 그 값 자체가 없어 자동채움이 조용히 실패한다.
 */
public final class CategoryIdResolver {

    private CategoryIdResolver() {
    }

    public record CategoryIds(long majorCategoryId, long categoryId) {
    }

    // 남성 기준(33종, majorCategoryId 4~9). {소분류 코드 -> (majorCategoryId, categoryId)}.
    private static final Map<String, CategoryIds> MEN_IDS = Map.ofEntries(
            Map.entry("JACKET", new CategoryIds(4, 24)),
            Map.entry("COAT", new CategoryIds(4, 25)),
            Map.entry("CARDIGAN", new CategoryIds(4, 26)),
            Map.entry("PADDED_JACKET", new CategoryIds(4, 27)),
            Map.entry("HOOD_ZIPUP", new CategoryIds(4, 28)),
            Map.entry("TSHIRT", new CategoryIds(5, 29)),
            Map.entry("SHIRT", new CategoryIds(5, 30)),
            Map.entry("KNIT", new CategoryIds(5, 31)),
            Map.entry("HOODIE", new CategoryIds(5, 32)),
            Map.entry("SWEATSHIRT", new CategoryIds(5, 33)),
            Map.entry("SLEEVELESS", new CategoryIds(5, 34)),
            Map.entry("DENIM", new CategoryIds(6, 35)),
            Map.entry("SLACKS", new CategoryIds(6, 36)),
            Map.entry("CARGO_PANTS", new CategoryIds(6, 37)),
            Map.entry("SKIRT", new CategoryIds(6, 38)),
            Map.entry("SHORT_PANTS", new CategoryIds(6, 39)),
            Map.entry("JOGGER_PANTS", new CategoryIds(6, 40)),
            Map.entry("COTTON_PANTS", new CategoryIds(6, 41)),
            Map.entry("SNEAKERS", new CategoryIds(7, 42)),
            Map.entry("BOOTS", new CategoryIds(7, 43)),
            Map.entry("DRESS_SHOES", new CategoryIds(7, 44)),
            Map.entry("SANDALS_SLIPPERS", new CategoryIds(7, 45)),
            Map.entry("BACKPACK", new CategoryIds(8, 46)),
            Map.entry("SHOULDER_BAG", new CategoryIds(8, 47)),
            Map.entry("TOTE_BAG", new CategoryIds(8, 48)),
            Map.entry("CROSS_BAG", new CategoryIds(8, 49)),
            Map.entry("POUCH", new CategoryIds(8, 50)),
            Map.entry("HAT", new CategoryIds(9, 51)),
            Map.entry("BELT", new CategoryIds(9, 52)),
            Map.entry("SCARF", new CategoryIds(9, 53)),
            Map.entry("JEWELRY", new CategoryIds(9, 54)),
            Map.entry("WATCH", new CategoryIds(9, 55)),
            Map.entry("SUNGLASSES", new CategoryIds(9, 56)));

    // 남성에 없는 소분류만 — 여성 기준으로 폴백(원피스 및 점프슈트, majorCategoryId=16).
    private static final Map<String, CategoryIds> WOMEN_ONLY_IDS = Map.ofEntries(
            Map.entry("DRESS", new CategoryIds(16, 90)),
            Map.entry("JUMPSUIT", new CategoryIds(16, 91)));

    /** 소분류 코드로 (majorCategoryId, categoryId)를 계산한다. 알 수 없는 코드면 {@code null}. */
    public static CategoryIds resolve(String subcategoryCode) {
        CategoryIds ids = MEN_IDS.get(subcategoryCode);
        return ids != null ? ids : WOMEN_ONLY_IDS.get(subcategoryCode);
    }
}
