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

    /**
     * 경매를 시작한다(AUCT-002). {@code READY → RUNNING}이며 종료 예정 시각이 이때 확정된다.
     *
     * <p><b>시각은 서버가 준다.</b> 종료 판정도 서버 시각 기준이라 시간 축이 둘로 갈리면
     * "브라우저에서는 아직 남았는데 서버는 이미 끝난" 구간이 생긴다(erd.md §6).
     *
     * <p>전이 가능 여부는 {@link #isReady()}로 미리 확인해야 한다 — 왜 안 되는지를 에러 코드로
     * 구분해 돌려주는 책임은 서비스에 있다.
     */
    public void start(LocalDateTime at) {
        this.status = AuctionStatus.RUNNING;
        this.startedAt = at;
        this.scheduledEndAt = at.plusSeconds(durationSeconds);
    }

    public boolean isReady() {
        return status == AuctionStatus.READY;
    }

    public boolean isRunning() {
        return status == AuctionStatus.RUNNING;
    }

    /**
     * 다음에 넣어야 하는 최소 입찰가.
     *
     * <p><b>첫 입찰은 시작가 그대로다.</b> 시작가에 증액 단위를 더해 버리면 시작가로는 아무도
     * 살 수 없게 되어 "시작가"라는 말이 무의미해진다. 두 번째부터 현재가 + 증액 단위다.
     *
     * <p>FE 입찰 버튼이 이 값을 그대로 눌러 보내면 되도록 서버가 계산해 내려준다 — 클라이언트가
     * 같은 계산을 다시 하면 정책이 바뀔 때 두 곳이 어긋난다.
     */
    public long nextBidPrice() {
        return hasBid() ? currentPrice + bidUnit : startPrice;
    }

    /** 입찰이 한 번이라도 들어왔는지. 현재가가 아니라 최고 입찰자 유무로 판정한다 — 시작가가 0일 수 있다. */
    public boolean hasBid() {
        return topBidderId != null;
    }

    /** 종료 임박 시 자동 연장할 기준(초). 종료까지 이 값 이하로 남았으면 입찰이 들어올 때마다 밀린다. */
    private static final int EXTEND_THRESHOLD_SECONDS = 3;

    /** 한 번 연장될 때 늘어나는 시간(초). */
    private static final int EXTEND_BY_SECONDS = 5;

    /**
     * 지금 입찰을 받을 수 있는 상태인지(AUCT-002~006). {@code RUNNING}이고 종료 예정 시각
     * 전이어야 한다 — 스케줄러가 아직 강제 종료 처리를 하지 않았더라도, 시각이 지났으면
     * 더 이상 유효한 입찰이 아니다.
     */
    public boolean isOpenForBidding(LocalDateTime at) {
        return isRunning() && scheduledEndAt != null && at.isBefore(scheduledEndAt);
    }

    /**
     * 이 회원이 지금 입찰할 수 있는지(AUCT-006). <b>직전 최고 입찰자 본인은 연속으로 입찰할 수
     * 없다</b> — 자기 자신을 상위 입찰하는 것은 의미가 없고, 포인트 보류 쪽에서도 "이미 HELD를
     * 쥐고 있어 두 번째 보류를 만들 수 없다"는 전제가 이 규칙에 기대고 있다.
     */
    public boolean isBiddableBy(Long bidderId) {
        return !hasBid() || !topBidderId.equals(bidderId);
    }

    /**
     * 요청한 금액이 지금 유효한 입찰가인지. <b>{@link #nextBidPrice()}와 정확히 같아야 한다</b>
     * (erd.md §4) — 그 이상도 허용하면 "얼마를 불렀는지"가 불명확해지고, FE가 그 값을 그대로
     * 보내도록 설계했으므로 어긋난 값은 화면이 낡았다는 신호다.
     */
    public boolean isValidBidPrice(Long bidPrice) {
        return bidPrice != null && bidPrice.longValue() == nextBidPrice();
    }

    /**
     * 새 최고 입찰을 반영한다. 유효성 검증({@link #isOpenForBidding}·{@link #isBiddableBy}·
     * {@link #isValidBidPrice})은 서비스가 미리 확인해야 한다 — 여기서 다시 막지 않는 이유는
     * {@link #transitionTo}와 같다.
     *
     * <p>종료 임박(3초 이하) 입찰이면 <b>같은 문장에서</b> 5초 연장한다(AUCT-010) — 별도
     * 트랜잭션으로 나누면 그 사이에 다른 입찰이 끼어들 여지가 생긴다.
     */
    public void applyBid(Long bidderId, long bidPrice, LocalDateTime at) {
        this.topBidderId = bidderId;
        this.currentPrice = bidPrice;
        if (!scheduledEndAt.minusSeconds(EXTEND_THRESHOLD_SECONDS).isAfter(at)) {
            this.scheduledEndAt = scheduledEndAt.plusSeconds(EXTEND_BY_SECONDS);
            this.extensionCount = (short) (extensionCount + 1);
        }
    }

    /**
     * 종료 예정 시각이 지났는지(AUCT-012 마감 스캐너 판정).
     *
     * <p>{@link #isOpenForBidding}의 반대가 아니다 — 저쪽은 "지금 입찰을 받을 수 있는가", 이쪽은
     * "이제 마감해야 하는가"다. {@code RUNNING}이 아닌 경매는 마감 대상이 아니다.
     */
    public boolean isDue(LocalDateTime at) {
        return isRunning() && scheduledEndAt != null && !at.isBefore(scheduledEndAt);
    }

    /**
     * 낙찰로 마감한다(AUCT-012). 낙찰자·낙찰가는 최고 입찰자·현재가를 그대로 확정한다.
     *
     * <p>입찰이 있는지({@link #hasBid()})는 서비스가 미리 확인해야 한다 — 입찰이 없는데 이걸
     * 부르면 {@code ck_auction_success_fields} 제약에 걸린다.
     */
    public void closeAsSuccess(LocalDateTime at) {
        this.status = AuctionStatus.SUCCESS;
        this.winnerId = topBidderId;
        this.finalPrice = currentPrice;
        this.endedAt = at;
    }

    /**
     * 유찰로 마감한다(AUCT-014) — 입찰이 하나도 없이 끝난 경우다.
     *
     * <p><b>{@code winnerId}·{@code finalPrice}는 비워 둔다.</b> 그래서 유찰 이력은 상품 상태가
     * 아니라 이 행 하나로 남는다(설계 판단 10 정정).
     */
    public void closeAsFailed(LocalDateTime at) {
        this.status = AuctionStatus.FAILED;
        this.endedAt = at;
    }
}