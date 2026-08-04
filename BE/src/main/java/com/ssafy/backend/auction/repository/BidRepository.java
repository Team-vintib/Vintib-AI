package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Bid;
import com.ssafy.backend.auction.entity.BidStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BidRepository extends JpaRepository<Bid, Long> {

    /** 경매 snapshot 의 입찰 횟수(AUCT-002). 밀린 입찰(OUTBID)도 "몇 번 붙었는지"에 포함한다. */
    long countByAuction_Id(Long auctionId);

    /**
     * 이 경매의 현재 활성 입찰(있다면 항상 최대 1건). 상위 입찰이 들어오면 이 건을
     * {@code OUTBID}로 내리기 위해 찾는다.
     */
    Optional<Bid> findByAuction_IdAndStatus(Long auctionId, BidStatus status);

    /**
     * 입찰 내역 커서 페이징(AUCT-003). {@code ChatMessageRepository.findPageByLiveId}와 같은
     * 이유로 커서를 {@code createdAt}이 아니라 {@code id}로 잡는다 — 입찰도 조회 중에 계속
     * 쌓이는 데이터라 같은 밀리초 동률·offset 밀림 문제가 똑같이 생긴다.
     */
    @Query("""
            select b
            from Bid b
            join fetch b.bidder
            where b.auction.id = :auctionId
              and (:cursor is null or b.id < :cursor)
            order by b.id desc
            """)
    List<Bid> findPageByAuctionId(
            @Param("auctionId") Long auctionId, @Param("cursor") Long cursor, Pageable pageable);
}
