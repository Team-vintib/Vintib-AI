package com.ssafy.backend.point.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapsId;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 포인트 잔액 집계(MY-007). {@code member_body_profile}/{@code business_info}와 같은
 * 공유 PK 1:1 구조 — 회원당 한 행만 존재한다.
 *
 * <p>잔액을 상태 컬럼이 아니라 버킷별로 나눠 들고 있다({@code available/bidHeld/tradeEscrow/
 * settling/withdrawing}) — 기능정의서 §4.9 포인트 상태 6종을 잔액 버킷으로 구현한 것이다.
 * 입찰 보류(bidHeld)는 경매 입찰이 아직 없어(AUCT-003 이후) 항상 0이다. 거래 대금 보관(tradeEscrow)은
 * {@link #pay}(주문 결제)로 채워지고 {@link #releaseEscrow}(구매 확정)로 빠진다 — 정산 대기(settling)는
 * 쓰지 않고 {@link #settle}로 판매자 available에 바로 반영한다.
 */
@Entity
@Table(name = "point_account")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PointAccount {

    @Id
    private Long memberId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id")
    private Member member;

    @Column(nullable = false)
    private Long available;

    @Column(name = "bid_held", nullable = false)
    private Long bidHeld;

    @Column(name = "trade_escrow", nullable = false)
    private Long tradeEscrow;

    @Column(nullable = false)
    private Long settling;

    @Column(nullable = false)
    private Long withdrawing;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Builder
    private PointAccount(Member member) {
        this.member = member;
        this.available = 0L;
        this.bidHeld = 0L;
        this.tradeEscrow = 0L;
        this.settling = 0L;
        this.withdrawing = 0L;
        this.updatedAt = LocalDateTime.now();
    }

    /** 결제 연동 없이 금액만 반영한다(테스트/데모 전용) — available 버킷에 더한다. */
    public void charge(long amount) {
        this.available += amount;
        this.updatedAt = LocalDateTime.now();
    }

    /** 잔액 검증은 서비스가 미리 한다 — available을 줄이고 withdrawing으로 옮긴다. */
    public void withdraw(long amount) {
        this.available -= amount;
        this.withdrawing += amount;
        this.updatedAt = LocalDateTime.now();
    }

    /** 주문 결제(SALE-002) — 잔액 검증은 서비스가 미리 한다. available을 줄이고 tradeEscrow로 옮겨 보관한다. */
    public void pay(long amount) {
        this.available -= amount;
        this.tradeEscrow += amount;
        this.updatedAt = LocalDateTime.now();
    }

    /** 구매 확정(ORDER-002/003) 구매자 측 — 보관하던 금액을 내보낸다(판매자 정산은 {@link #settle}). */
    public void releaseEscrow(long amount) {
        this.tradeEscrow -= amount;
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * 구매 확정(ORDER-002/003) 판매자 측 — 정산 대기 절차가 아직 없어 {@code settling}을 거치지
     * 않고 바로 available로 반영한다.
     */
    public void settle(long amount) {
        this.available += amount;
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * 환불 승인(REFUND-002) 구매자 측 — 판매자에게 정산하지 않고 보관하던 금액을 그대로 돌려준다.
     * {@link #releaseEscrow}와 달리 여기서는 available까지 함께 채운다.
     */
    public void refund(long amount) {
        this.tradeEscrow -= amount;
        this.available += amount;
        this.updatedAt = LocalDateTime.now();
    }
}