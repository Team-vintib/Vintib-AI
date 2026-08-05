package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.LiveProduct;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

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
}