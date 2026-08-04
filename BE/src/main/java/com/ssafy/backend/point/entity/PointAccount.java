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
 * 입찰 보류(bidHeld)·거래 대금 보관(tradeEscrow)·정산 대기(settling)는 경매/주문 트랜잭션이
 * 실제로 발생해야 채워지는데, 이번 범위(MY-007)에는 그 트리거가 없어 항상 0이다 —
 * {@link #charge}(충전)/{@link #withdraw}(출금)로 {@code available}만 오간다.
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

    /** 잔액이 충분한지. 보류 전에 서비스가 먼저 확인해 부족하면 400으로 돌려준다 — DB
     *  {@code ck_point_non_negative}까지 가면 500이 된다. */
    public boolean hasEnoughAvailable(long amount) {
        return available >= amount;
    }

    /**
     * 입찰 보류(AUCT-007). {@code available}에서 빼 {@code bidHeld}로 옮긴다.
     * 잔액 검증은 {@link #hasEnoughAvailable}로 서비스가 미리 한다.
     */
    public void holdForBid(long amount) {
        this.available -= amount;
        this.bidHeld += amount;
        this.updatedAt = LocalDateTime.now();
    }

    /** 보류 해제(AUCT-008). 상위 입찰에 밀리거나 경매가 유찰됐을 때 {@code bidHeld}를 되돌린다. */
    public void releaseHold(long amount) {
        this.bidHeld -= amount;
        this.available += amount;
        this.updatedAt = LocalDateTime.now();
    }
}
