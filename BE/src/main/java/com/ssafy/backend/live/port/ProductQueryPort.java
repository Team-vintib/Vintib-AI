package com.ssafy.backend.live.port;

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
     * 라이브가 상품에 대해 알아야 하는 최소 정보.
     *
     * @param id        상품 ID
     * @param sellerId  판매자 회원 ID — 방송 호스트 본인 상품인지 확인하는 데 쓴다
     * @param title     상품명 — 시청 화면·연결 목록 표시용
     */
    record ProductSummary(Long id, Long sellerId, String title) {
    }
}
