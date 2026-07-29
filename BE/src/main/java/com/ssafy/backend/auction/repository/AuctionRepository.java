package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.entity.AuctionStatus;
import java.util.Collection;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuctionRepository extends JpaRepository<Auction, Long> {

    /**
     * 같은 라이브·상품에 아직 끝나지 않은 경매가 있는지. 조건을 두 번 거는 것을 막는 데 쓴다
     * (종료·취소된 경매는 재설정을 허용해야 하므로 상태를 지정해 받는다).
     */
    boolean existsByLiveIdAndProductIdAndStatusIn(
            Long liveId, Long productId, Collection<AuctionStatus> statuses);
}