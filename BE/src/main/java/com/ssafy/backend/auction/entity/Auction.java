package com.ssafy.backend.auction.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.live.entity.Live;
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
 * 라이브 안에서 진행되는 상품 1건의 경매.
 *
 * <p>스키마는 {@code docs/db/schema.sql}의 {@code auction} 테이블이 단일 기준이다.
 * 이번 단계(AUCT-001)에서 채워지는 것은 <b>조건뿐</b>이다 — 시작가·증액 단위·진행 시간.
 * 진행 관련 필드({@code currentPrice}, {@code topBidderId}, {@code scheduledEndAt},
 * {@code extensionCount}, {@code winnerId}, {@code finalPrice})는 매핑만 해 두고
 * 실제 갱신은 경매 시작·입찰(AUCT-002 이후, 다음 주)에서 다룬다.
 *
 * <p><b>DB 제약이 함께 지키는 것</b> — "한 라이브에서 동시에 진행 중인 경매는 1개"(LIVE-004)는
 * {@code ux_auction_live_running}(부분 UNIQUE 인덱스)으로 막혀 있다. JPA로는 표현할 수 없는
 * 형태라 DDL이 소유한다. 입찰 동시성의 1차 방어는 애플리케이션 락이고, 이 제약들은
 * 락이 실패했을 때의 안전망이다 (erd.md §4).
 */
@Entity
@Table(
        name = "auction",
        check = {
                @CheckConstraint(
                        name = "ck_auction_status",
                        constraint = "status IN ("
                                + "'READY', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELED')"),
                @CheckConstraint(name = "ck_auction_bid_unit", constraint = "bid_unit > 0"),
                @CheckConstraint(name = "ck_auction_start_price", constraint = "start_price >= 0"),
                @CheckConstraint(
                        name = "ck_auction_success_fields",
                        constraint = "status <> 'SUCCESS' "
                                + "OR (winner_id IS NOT NULL AND final_price IS NOT NULL)")
        })
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Auction extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "live_id", nullable = false)
    private Live live;

    // 상품 도메인(서윤)은 아직 완성 전이라 연관관계 대신 식별자만 들고 있는다.
    // 조회가 필요하면 live 도메인의 ProductQueryPort 를 거친다 (계획 005: 교체점 국소화).
    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "start_price", nullable = false)
    private Long startPrice;

    @Column(name = "bid_unit", nullable = false)
    private Long bidUnit;

    @Column(name = "duration_seconds", nullable = false)
    private Integer durationSeconds;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AuctionStatus status;

    /** 현재가. 입찰이 없으면 0이다 (AUCT-011 실시간 표시를 위한 비정규화 값). */
    @Column(name = "current_price", nullable = false)
    private Long currentPrice;

    // 최고 입찰자·낙찰자는 입찰 트랜잭션에서 초당 여러 번 갱신되는 자리다.
    // FK 대입만을 위해 Member 를 로딩하지 않도록 식별자로 둔다.
    @Column(name = "top_bidder_id")
    private Long topBidderId;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    /** 종료 예정 시각. 마감 직전 입찰이 들어오면 5초씩 밀린다 (AUCT-010). */
    @Column(name = "scheduled_end_at")
    private LocalDateTime scheduledEndAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    /** 연장 횟수. 제한은 없으나 이상 동작 검증·통계에 쓴다. */
    @Column(name = "extension_count", nullable = false)
    private Short extensionCount;

    @Column(name = "winner_id")
    private Long winnerId;

    @Column(name = "final_price")
    private Long finalPrice;

    private Auction(Live live, Long productId, Long startPrice, Long bidUnit, Integer durationSeconds) {
        this.live = live;
        this.productId = productId;
        this.startPrice = startPrice;
        this.bidUnit = bidUnit;
        this.durationSeconds = durationSeconds;
        this.status = AuctionStatus.READY;
        this.currentPrice = 0L;
        this.extensionCount = 0;
    }

    /**
     * 경매 조건 설정(AUCT-001). 아직 시작 전이므로 {@code READY} 상태로 만들어진다.
     *
     * <p>상품이 이 라이브에 연결돼 있는지(미등록 상품 불가)는 서비스에서 검증한다.
     */
    public static Auction configure(
            Live live, Long productId, Long startPrice, Long bidUnit, Integer durationSeconds) {
        return new Auction(live, productId, startPrice, bidUnit, durationSeconds);
    }
}