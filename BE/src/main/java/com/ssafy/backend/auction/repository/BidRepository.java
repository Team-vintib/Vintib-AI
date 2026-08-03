package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Bid;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BidRepository extends JpaRepository<Bid, Long> {

    /** 경매 snapshot 의 입찰 횟수(AUCT-002). 밀린 입찰(OUTBID)도 "몇 번 붙었는지"에 포함한다. */
    long countByAuction_Id(Long auctionId);
}
