package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

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
}