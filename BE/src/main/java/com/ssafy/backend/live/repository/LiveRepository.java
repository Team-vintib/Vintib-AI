package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import java.util.Collection;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface LiveRepository extends JpaRepository<Live, Long> {

    /**
     * 공개 라이브 목록. 상태 필터·카테고리 필터(선택)·호스트 필터(선택, MY-005)를 함께 건다.
     *
     * <p>카테고리 필터는 <b>상품 ID 집합으로 환원해서</b> 받는다 — 라이브 도메인이 상품·카테고리
     * 테이블을 직접 조인하지 않도록 {@code ProductQueryPort}가 먼저 ID를 뽑아 주고, 여기서는
     * 자기 도메인인 {@code LiveProduct}만 본다.
     *
     * <p>호스트 필터는 마이페이지 라이브 관리(MY-005)가 쓴다 — 본인 조회일 때는 컨트롤러가
     * {@code statuses}에 종료·취소까지 넣어 함께 넘긴다.
     *
     * @param filterByCategory 카테고리 필터를 걸지 여부. false면 {@code productIds}는 무시된다
     * @param filterByHost     호스트 필터를 걸지 여부. false면 {@code hostId}는 무시된다
     */
    @Query("""
            SELECT l FROM Live l
            WHERE l.status IN :statuses
              AND (:filterByCategory = false
                   OR EXISTS (SELECT 1 FROM LiveProduct lp
                              WHERE lp.live = l
                                AND lp.removedAt IS NULL
                                AND lp.productId IN :productIds))
              AND (:filterByHost = false OR l.host.id = :hostId)
            """)
    Page<Live> findPublicLives(
            @Param("statuses") Collection<LiveStatus> statuses,
            @Param("filterByCategory") boolean filterByCategory,
            @Param("productIds") Collection<Long> productIds,
            @Param("filterByHost") boolean filterByHost,
            @Param("hostId") Long hostId,
            Pageable pageable);

    /**
     * 최고 시청자 수를 끌어올린다. 지금 값보다 크지 않으면 아무 행도 바뀌지 않는다.
     *
     * <p><b>읽고 비교한 뒤 쓰지 않는 이유.</b> 시청자가 동시에 들어오면 두 스레드가 같은 최고치를
     * 읽고 각자 덮어써 더 큰 값이 사라질 수 있다. 조건을 {@code WHERE} 에 두면 갱신 판정과 쓰기가
     * 한 문장에서 원자적으로 끝난다.
     *
     * @return 실제로 갱신된 행 수(0 또는 1)
     */
    @Transactional
    @Modifying
    @Query("""
            UPDATE Live l SET l.peakViewerCount = :count
            WHERE l.id = :liveId AND l.peakViewerCount < :count
            """)
    int raisePeakViewerCount(@Param("liveId") Long liveId, @Param("count") int count);
}