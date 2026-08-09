package com.ssafy.backend.live.port;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 라이브 도메인이 상품 도메인을 들여다보는 유일한 창구.
 *
 * <p>라이브는 상품의 내부 구조(판매 상태 enum, 가격 정책 등)를 알 필요가 없다. 방송에 걸 수 있는
 * 상품인지 판단하는 데 필요한 최소 정보만 이 포트를 통해 가져온다. 상품 도메인이 바뀌어도
 * 영향 범위가 어댑터 한 곳으로 좁혀진다.
 */
public interface ProductQueryPort {

    /**
     * 상품 요약 조회. 없으면 {@link Optional#empty()}.
     */
    Optional<ProductSummary> findById(Long productId);

    /**
     * 주어진 상품들이 속한 <b>대분류</b> 카테고리 집합. 중복은 제거되고 ID 오름차순으로 정렬된다.
     *
     * <p>상품은 소분류(자켓·스카프)에 달리지만 라이브 카드에 붙는 배지는 대분류(아우터·액세서리)다.
     * 소분류를 그대로 노출하면 배지가 대여섯 개씩 붙어 읽히지 않는다. 그래서 여기서 부모로 올린다.
     */
    List<CategorySummary> findRootCategories(Collection<Long> productIds);

    /**
     * 상품 ID → 그 상품이 속한 대분류 카테고리 매핑.
     *
     * <p>목록 화면처럼 라이브 여러 건의 카테고리를 한 번에 구할 때 쓴다. 라이브마다
     * {@link #findRootCategories}를 부르면 N+1이 된다.
     */
    Map<Long, CategorySummary> findRootCategoryByProductId(Collection<Long> productIds);

    /**
     * 주어진 카테고리에 속한 상품 ID 목록. <b>대분류를 주면 그 하위 소분류 상품까지 포함한다.</b>
     *
     * <p>목록 화면의 카테고리 필터가 쓴다 — 사용자가 '아우터'를 고르면 자켓·코트 상품을 건
     * 라이브가 모두 나와야 하고, '스카프'를 고르면 스카프 상품을 건 라이브만 나와야 한다.
     */
    List<Long> findProductIdsInCategories(Collection<Long> categoryIds);

    /**
     * 시청 화면 상품 카드에 필요한 정보를 한 번에.
     *
     * <p>편성 상품 하나하나에 대해 상품·브랜드·이미지를 따로 조회하면 상품 수만큼 쿼리가 나간다.
     * 시청 화면은 진입할 때마다 열리므로 그 비용이 그대로 쌓인다.
     *
     * @param productIds 비어 있으면 빈 map
     */
    Map<Long, ProductCard> findCards(Collection<Long> productIds);

    /**
     * 라이브가 상품에 대해 알아야 하는 최소 정보.
     *
     * @param id        상품 ID
     * @param sellerId  판매자 회원 ID — 방송 호스트 본인 상품인지 확인하는 데 쓴다
     * @param title     상품명 — 시청 화면·연결 목록 표시용
     */
    record ProductSummary(Long id, Long sellerId, String title) {
    }

    /**
     * 시청 화면 상품 카드 한 장(FE 요청 {@code docs/requests/FE/006}).
     *
     * <p><b>{@code saleType}·{@code saleStatus}를 문자열로 받는 이유.</b> 이 포트는 라이브가 상품의
     * 내부 구조를 모르게 하려고 둔 것이라 상품 도메인 enum을 그대로 노출하지 않는다. 값은 FE로
     * 그대로 흘러갈 뿐 라이브 쪽에서 분기하지 않는다.
     *
     * @param brandName      브랜드명. 브랜드 미지정 상품은 {@code null}
     * @param price          정찰제가. 경매 예정 상품은 아직 가격이 없어 {@code null}
     * @param saleType       {@code DIRECT_SALE} / {@code AUCTION}. 판매 방식 미정이면 {@code null}
     * @param saleStatus     판매 상태. {@code DRAFT} / {@code ON_SALE} / {@code AUCTION_SCHEDULED} /
     *                       {@code AUCTION_IN_PROGRESS} / {@code SOLD}. <b>판매 방식과 별개 축이다</b> —
     *                       경매 상품도 팔리면 {@code SOLD}가 된다
     * @param conditionGrade 중고 상태 등급. 등급 체계가 미확정이라 자유 문자열이다
     * @param thumbnailUrl   대표 이미지 URL. 등록된 이미지가 없으면 {@code null}
     * @param material       소재. 등록하지 않았으면 {@code null}(FE 요청 003 §3.5 선택 필드)
     * @param measurements   실측 치수(cm). 항목이 상품마다 달라 키-값으로 받는다. 없으면 {@code null}
     * @param defectSummary  하자 요약. 등록된 하자 항목을 순서대로 이어 붙인 문자열. 없으면 {@code null}
     *                       — FE는 목록 형태가 아니라 한 줄 요약을 요청했다(003 §3.5)
     */
    record ProductCard(
            Long id,
            String title,
            String brandName,
            Long price,
            String saleType,
            String saleStatus,
            String conditionGrade,
            String thumbnailUrl,
            String material,
            Map<String, Integer> measurements,
            String defectSummary) {
    }

    /** 카테고리 표시용 최소 정보. */
    record CategorySummary(Long id, String name) {
    }
}