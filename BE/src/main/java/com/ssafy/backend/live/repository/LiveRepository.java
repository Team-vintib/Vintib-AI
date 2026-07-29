package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import java.util.Collection;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LiveRepository extends JpaRepository<Live, Long> {

    /**
     * 공개 라이브 목록. 상태 필터와 카테고리 필터(선택)를 함께 건다.
     *
     * <p>카테고리 필터는 <b>상품 ID 집합으로 환원해서</b> 받는다 — 라이브 도메인이 상품·카테고리
     * 테이블을 직접 조인하지 않도록 {@code ProductQueryPort}가 먼저 ID를 뽑아 주고, 여기서는
     * 자기 도메인인 {@code LiveProduct}만 본다.
     *
     * @param filterByCategory 카테고리 필터를 걸지 여부. false면 {@code productIds}는 무시된다
     */
    @Query("""
            SELECT l FROM Live l
            WHERE l.status IN :statuses
              AND (:filterByCategory = false
                   OR EXISTS (SELECT 1 FROM LiveProduct lp
                              WHERE lp.live = l
                                AND lp.removedAt IS NULL
                                AND lp.productId IN :productIds))
            """)
    Page<Live> findPublicLives(
            @Param("statuses") Collection<LiveStatus> statuses,
            @Param("filterByCategory") boolean filterByCategory,
            @Param("productIds") Collection<Long> productIds,
            Pageable pageable);
}