package com.ssafy.backend.live.port;

import java.util.Collection;
import java.util.List;
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
     * 라이브가 상품에 대해 알아야 하는 최소 정보.
     *
     * @param id        상품 ID
     * @param sellerId  판매자 회원 ID — 방송 호스트 본인 상품인지 확인하는 데 쓴다
     * @param title     상품명 — 시청 화면·연결 목록 표시용
     */
    record ProductSummary(Long id, Long sellerId, String title) {
    }

    /** 카테고리 표시용 최소 정보. */
    record CategorySummary(Long id, String name) {
    }
}