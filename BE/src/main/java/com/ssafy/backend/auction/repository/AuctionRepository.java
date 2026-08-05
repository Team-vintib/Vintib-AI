package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuctionRepository extends JpaRepository<Auction, Long> {

    /**
     * 같은 라이브·상품에 아직 끝나지 않은 경매가 있는지. 조건을 두 번 거는 것을 막는 데 쓴다
     * (종료·취소된 경매는 재설정을 허용해야 하므로 상태를 지정해 받는다).
     */
    boolean existsByLiveIdAndProductIdAndStatusIn(
            Long liveId, Long productId, Collection<AuctionStatus> statuses);

    /**
     * 홈 "경매 예정" 카드(HOME-001)용 — 상품에 걸린 경매를 한 번에.
     *
     * <p>카드가 시작가와 시작 예정 시각을 함께 보여 주는데, 시작 예정 시각은 경매가 아니라
     * <b>그 경매가 얹힌 방송의 예정 시각</b>이다({@code auction.live_id}는 NOT NULL). 그래서
     * {@code live}를 함께 당겨 온다 — 상품 수만큼 방송을 다시 조회하면 N+1이 된다.
     */
    @EntityGraph(attributePaths = "live")
    List<Auction> findByProductIdIn(Collection<Long> productIds);

    /**
     * 라이브 진입 시 경매 패널을 채울 경매 하나(AUCT-002).
     *
     * <p><b>진행 중이 준비 중보다 우선한다.</b> 지금 입찰할 수 있는 경매가 있는데 다음 예정
     * 경매를 보여 주면 시청자가 입찰 기회를 놓친다. 같은 상태 안에서는 최근에 만든 것이 앞이다.
     *
     * <p>종료된 경매(SUCCESS/FAILED/CANCELED)는 대상이 아니다 — 끝난 경매를 패널에 띄우면
     * 남은 시간이 음수인 화면이 된다. 낙찰 결과는 종료 이벤트로 전달한다.
     *
     * <p>{@code CASE} 로 정렬하는 이유는, 상태 두 개를 따로 조회하면 왕복이 두 번이 되고
     * "RUNNING 을 먼저"라는 규칙이 호출부로 새기 때문이다.
     */
    @EntityGraph(attributePaths = "live")
    @Query("""
            SELECT a FROM Auction a
            WHERE a.live.id = :liveId
              AND a.status IN (com.ssafy.backend.auction.entity.AuctionStatus.RUNNING,
                               com.ssafy.backend.auction.entity.AuctionStatus.READY)
            ORDER BY CASE WHEN a.status = com.ssafy.backend.auction.entity.AuctionStatus.RUNNING
                          THEN 0 ELSE 1 END ASC,
                     a.createdAt DESC,
                     a.id DESC
            """)
    List<Auction> findPanelCandidates(@Param("liveId") Long liveId, Pageable pageable);

    /**
     * 이 라이브에 진행 중인 경매가 이미 있는지(LIVE-004).
     *
     * <p>애플리케이션 1차 방어다. 원래는 부분 UNIQUE 인덱스 {@code ux_auction_live_running}가
     * 최후 방어선인데, <b>Hibernate 의 {@code ddl-auto} 는 부분 인덱스를 만들지 못한다</b> —
     * 그래서 {@code PartialIndexInitializer}가 기동 시 따로 만든다.
     */
    boolean existsByLiveIdAndStatus(Long liveId, AuctionStatus status);

    @EntityGraph(attributePaths = "live")
    Optional<Auction> findWithLiveById(Long id);

    /**
     * 입찰 처리용 행 잠금 조회(AUCT-003).
     *
     * <p><b>이 프로젝트의 입찰 동시성 1차 방어다.</b> 같은 경매에 대한 입찰 요청은 이 잠금으로
     * 직렬화된다 — 두 요청이 동시에 들어와도 하나가 끝나야 다음이 시작되므로 "락은 풀렸는데
     * 커밋은 안 된" 창이 원리적으로 없다(트랜잭션과 잠금의 생명주기가 같다). Redis 분산락이나
     * MQ는 검토 후 채택하지 않았다 — 이유는 계획 문서(JY008) 설계 판단 1 참고.
     *
     * <p>{@code ux_bid_auction_price} 부분 UNIQUE 인덱스는 이 잠금이 실패했을 때(버그·재시도
     * 등)의 최후 방어선이지, 대체재가 아니다.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM Auction a WHERE a.id = :id")
    Optional<Auction> findByIdForUpdate(@Param("id") Long id);

    /**
     * 마감할 때가 된 경매(AUCT-012 마감 스캐너). {@code RUNNING}이면서 종료 예정 시각이 지난 것들.
     *
     * <p><b>여기서는 잠그지 않는다.</b> 스캐너는 후보만 고르고, 실제 마감은 경매 하나하나를
     * {@link #findByIdForUpdate}로 다시 잡아 처리한다 — 목록 전체를 잠근 채로 마감·주문 생성·
     * 포인트 전환까지 돌리면 그동안 그 방송들의 입찰이 전부 멈춘다.
     *
     * <p>그래서 후보를 고른 시점과 잠그는 시점 사이에 마감 직전 입찰이 들어와 종료 시각이
     * 밀릴 수 있다(AUCT-010). 잠근 뒤 {@code isDue}를 한 번 더 확인해 걸러낸다.
     */
    List<Auction> findByStatusAndScheduledEndAtLessThanEqual(
            AuctionStatus status, java.time.LocalDateTime at, Pageable pageable);

    /** 방송 종료 시 강제 마감 대상(AUCT-014) — 이 방송에서 아직 진행 중인 경매. */
    List<Auction> findByLiveIdAndStatus(Long liveId, AuctionStatus status);
}