package com.ssafy.backend.auction.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.CheckConstraint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 입찰 한 건(AUCT-003). 스키마는 {@code docs/db/schema.sql}의 {@code bid} 테이블이 단일 기준이다.
 *
 * <p><b>이번 단계(AUCT-002)에서는 읽기만 쓴다</b> — 경매 snapshot 의 입찰 횟수를 세는 용도다.
 * 입찰 등록은 다음 단계(AUCT-003~006)에서 비관적 락과 함께 다룬다. 그래도 엔티티를 먼저 두는
 * 이유는, 세는 대상이 없다고 snapshot 에 0을 하드코딩해 두면 그 값이 그대로 남기 때문이다.
 *
 * <p><b>{@code bidder}를 연관관계로 두는 이유.</b> 입찰 내역 화면이 입찰자 닉네임을 보여 줘야 하고
 * (AUCT-011), {@code auction.top_bidder_id}와 달리 입찰 건은 초당 여러 번 갱신되는 자리가 아니다.
 */
@Entity
@Table(
        name = "bid",
        check =
                @CheckConstraint(
                        name = "ck_bid_status",
                        constraint = "status IN ('ACTIVE', 'OUTBID', 'WON', 'LOST')"))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Bid {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "auction_id", nullable = false)
    private Auction auction;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "bidder_id", nullable = false)
    private Member bidder;

    @Column(name = "bid_price", nullable = false)
    private Long bidPrice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private BidStatus status;

    /**
     * 선착순 판정 기준(AUCT-005). <b>클라이언트 클릭 시각이 아니라 서버 수신 시각이다</b> —
     * 클라이언트 시각을 믿으면 시계를 조작해 앞자리를 가져갈 수 있다.
     */
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    private Bid(Auction auction, Member bidder, Long bidPrice, LocalDateTime at) {
        this.auction = auction;
        this.bidder = bidder;
        this.bidPrice = bidPrice;
        this.status = BidStatus.ACTIVE;
        this.createdAt = at;
    }

    /** 새 최고 입찰. 직전 최고 입찰을 {@link #outbid()}로 내리는 것은 서비스 책임이다. */
    public static Bid place(
            Auction auction, Member bidder, Long bidPrice, LocalDateTime at) {
        return new Bid(auction, bidder, bidPrice, at);
    }

    public void outbid() {
        this.status = BidStatus.OUTBID;
    }

    public void win() {
        this.status = BidStatus.WON;
    }

    public void lose() {
        this.status = BidStatus.LOST;
    }
}
