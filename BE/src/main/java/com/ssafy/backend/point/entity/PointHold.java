package com.ssafy.backend.point.entity;

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
 * 입찰 보류 — 입찰 내역과 포인트 보류를 잇는다(AUCT-007~009). 스키마는
 * {@code docs/db/schema.sql}의 {@code point_hold} 테이블이 단일 기준이다.
 *
 * <p><b>{@code auctionId}·{@code bidId}를 연관관계가 아니라 식별자로만 들고 있는다.</b>
 * {@code point} 패키지가 {@code auction} 패키지 엔티티를 직접 참조하면 반대 방향 결합이 생긴다
 * ({@code auction} 도메인이 {@code point} 엔티티를 쓰는 것은 이 도메인이 "포인트 상태"를
 * 표현하는 자연스러운 자리라 허용하지만, 그 반대는 순환 의존이 된다). {@code Auction.productId}가
 * 상품 도메인을 참조하지 않는 것과 같은 이유다.
 *
 * <p><b>한 회원이 가질 수 있는 {@code HELD}는 전체 경매를 통틀어 하나뿐이다</b> — DB 부분 UNIQUE
 * 인덱스 {@code ux_point_hold_member_active}가 강제한다. 이 성질이 AUCT-006(연속 입찰 금지)과
 * AUCT-009(다른 경매 동시 참여 금지)를 동시에 만족시킨다.
 *
 * <p>⚠️ <b>같은 회원의 재입찰에서 기존 보류를 먼저 해제하면 안 된다.</b> 해제 후 재생성하는
 * 순서로 구현하면 그 사이에 위 제약이 통과해 버려 무력화된다. 그래서 서비스는 "직전 최고
 * 입찰자가 본인이면 애초에 거부"(AUCT-006)를 먼저 걸어, 같은 회원이 자기 보류를 건드리는
 * 경로 자체를 만들지 않는다.
 */
@Entity
@Table(
        name = "point_hold",
        check =
                @CheckConstraint(
                        name = "ck_point_hold_status",
                        constraint = "status IN ('HELD', 'RELEASED', 'CONVERTED')"))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PointHold {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(name = "auction_id", nullable = false)
    private Long auctionId;

    @Column(name = "bid_id", nullable = false)
    private Long bidId;

    @Column(nullable = false)
    private Long amount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PointHoldStatus status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "released_at")
    private LocalDateTime releasedAt;

    private PointHold(Member member, Long auctionId, Long bidId, Long amount, LocalDateTime at) {
        this.member = member;
        this.auctionId = auctionId;
        this.bidId = bidId;
        this.amount = amount;
        this.status = PointHoldStatus.HELD;
        this.createdAt = at;
    }

    /** 새 최고 입찰의 보류를 만든다. 항상 {@code HELD}로 시작한다. */
    public static PointHold hold(Member member, Long auctionId, Long bidId, Long amount, LocalDateTime at) {
        return new PointHold(member, auctionId, bidId, amount, at);
    }

    public void release(LocalDateTime at) {
        this.status = PointHoldStatus.RELEASED;
        this.releasedAt = at;
    }
}
