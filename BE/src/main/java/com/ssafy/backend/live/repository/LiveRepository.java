package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import java.time.LocalDateTime;
import java.util.Collection;
import java.util.List;
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

    /** 공개 프로필(011 §3.3) — 공개 상태(예정/진행 중)의 방송 수. */
    long countByHost_IdAndStatusIn(Long hostId, Collection<LiveStatus> statuses);

    /**
     * 이 회원이 그 방송의 호스트인지(시청자 수 집계에서 호스트를 빼기 위해).
     *
     * <p>구독마다 불리므로 방송을 통째로 읽지 않고 존재 여부만 본다.
     */
    boolean existsByIdAndHost_Id(Long id, Long hostId);

    /**
     * 홈 "지금 라이브" 섹션(HOME-001) — 진행 중인 방송을 최근 시작순으로.
     *
     * <p><b>상태를 인자로 받지 않고 조건을 이름에 박은 이유.</b> 홈은 종료된 방송을 절대 보이면
     * 안 된다 — 실제로 그 버그가 있었다(FE 요청 004 §3.3). 호출부가 상태를 넘기게 두면 다시
     * 틀릴 수 있어, 여기서 {@code LIVE} 하나로 고정한다.
     */
    List<Live> findByStatusOrderByStartedAtDesc(LiveStatus status, Pageable pageable);

    /** 홈 "예정 라이브" 섹션(HOME-001) — 가장 임박한 순. 지난 예정은 호출부가 잘라 낸다. */
    List<Live> findByStatusAndScheduledAtAfterOrderByScheduledAtAsc(
            LiveStatus status, LocalDateTime from, Pageable pageable);

    /**
     * 예정 시각이 지난 예약 라이브(JY010 자동 시작). 오래 기다린 것부터 처리하도록 임박순으로
     * 정렬한다. 상한은 호출부(스케줄러)가 {@code pageable}로 건다.
     */
    List<Live> findByStatusAndScheduledAtLessThanEqualOrderByScheduledAtAsc(
            LiveStatus status, LocalDateTime now, Pageable pageable);

    /** 팔로잉 홈(HOME-002) — 팔로우한 판매자들의 진행 중·예정 방송. */
    List<Live> findByHost_IdInAndStatusInOrderByCreatedAtDesc(
            Collection<Long> hostIds, Collection<LiveStatus> statuses, Pageable pageable);

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