package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
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
}