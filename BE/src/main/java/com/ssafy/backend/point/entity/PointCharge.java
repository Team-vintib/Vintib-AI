package com.ssafy.backend.point.entity;

import com.ssafy.backend.member.entity.Member;
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
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 토스페이먼츠 결제위젯 충전 준비/승인 상태(POINT-001). {@code orderId}는 이 앱이 발급해 토스에
 * 넘기는 주문번호로, {@code orders} 테이블과는 무관하다.
 */
@Entity
@Table(name = "point_charge")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PointCharge {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(name = "order_id", nullable = false, unique = true, length = 64)
    private String orderId;

    @Column(nullable = false)
    private Long amount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PointChargeStatus status;

    @Column(name = "payment_key", length = 200)
    private String paymentKey;

    @Column(name = "approved_at")
    private LocalDateTime approvedAt;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Builder
    private PointCharge(Member member, String orderId, Long amount) {
        this.member = member;
        this.orderId = orderId;
        this.amount = amount;
        this.status = PointChargeStatus.READY;
        this.createdAt = LocalDateTime.now();
    }

    /** 결제 승인 성공(POINT-001). */
    public void markDone(String paymentKey, LocalDateTime approvedAt) {
        this.status = PointChargeStatus.DONE;
        this.paymentKey = paymentKey;
        this.approvedAt = approvedAt;
    }

    /** 결제 승인 실패 — 재시도는 새 orderId(readyCharge)로만 가능하다. */
    public void markFailed() {
        this.status = PointChargeStatus.FAILED;
    }
}
