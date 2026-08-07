package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.LiveProduct;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LiveProductRepository extends JpaRepository<LiveProduct, Long> {

    /** 현재 연결 중인 상품만 정렬 순서대로. 제외된 건({@code removedAt != null})은 뺀다. */
    List<LiveProduct> findByLiveIdAndRemovedAtIsNullOrderBySortOrderAsc(Long liveId);

    /** 목록 화면용 배치 조회. 라이브마다 따로 조회하면 N+1이 된다. */
    List<LiveProduct> findByLiveIdInAndRemovedAtIsNull(Collection<Long> liveIds);

    Optional<LiveProduct> findByLiveIdAndProductIdAndRemovedAtIsNull(Long liveId, Long productId);

    /** 상품 상세의 "연결된 라이브" 표시용 — 상품이 현재 어느 라이브에 연결돼 있는지 라이브 무관하게 찾는다. */
    Optional<LiveProduct> findByProductIdAndRemovedAtIsNull(Long productId);

    boolean existsByLiveIdAndProductIdAndRemovedAtIsNull(Long liveId, Long productId);

    long countByLiveIdAndRemovedAtIsNull(Long liveId);

    /**
     * 이 상품이 편성된 <b>진행 중</b> 방송의 ID(JY013). 정찰 구매가 일어났을 때 어느 방송의
     * 시청자에게 판매 사실을 전파할지 정하는 데 쓴다.
     *
     * <p><b>주문 요청의 {@code liveId} 를 쓰지 않는 이유.</b> 상품 상세 화면에서 사면 그 값이
     * 아예 없다. 그래도 그 상품이 진행 중 방송에 걸려 있으면 시청자 큐에서 빠져야 한다 —
     * 이미 팔린 상품이 큐에 남아 있으면 눌렀다가 에러를 보게 된다.
     *
     * <p>{@code ux_live_product_active} 는 {@code (live_id, product_id)} 라 한 상품이 여러 방송에
     * 걸릴 수 있다. 그중 진행 중인 것은 사실상 하나지만, 둘 이상이면 호출부가 판단하도록
     * 목록으로 돌려준다.
     */
    @Query("""
            SELECT lp.live.id FROM LiveProduct lp
            WHERE lp.productId = :productId
              AND lp.removedAt IS NULL
              AND lp.live.status = com.ssafy.backend.live.entity.LiveStatus.LIVE
            """)
    List<Long> findRunningLiveIdsByProductId(@Param("productId") Long productId);
}