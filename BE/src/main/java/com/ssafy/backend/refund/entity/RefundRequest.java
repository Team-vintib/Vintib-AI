package com.ssafy.backend.refund.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.order.entity.Order;
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
 * 환불 요청(REFUND-001/002). 구매자가 요청하고 판매자가 승인/거절한다({@code RefundService} 참고).
 * 상태 전이 메서드는 전제조건을 검증하지 않는다 — 검증은 서비스가 한다({@code Order}와 같은 패턴).
 */
@Entity
@Table(name = "refund_request")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class RefundRequest extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private RefundReason reason;

    @Column(name = "detail_reason", nullable = false, columnDefinition = "TEXT")
    private String detailReason;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RefundStatus status;

    @Column(name = "rejection_reason", columnDefinition = "TEXT")
    private String rejectionReason;

    @Column(name = "reviewed_at")
    private LocalDateTime reviewedAt;

    @Builder
    private RefundRequest(Order order, RefundReason reason, String detailReason) {
        this.order = order;
        this.reason = reason;
        this.detailReason = detailReason;
        this.status = RefundStatus.REQUESTED;
    }

    /** 승인(REFUND-002) — 포인트 환급은 서비스가 처리하고, 여기서는 상태만 바꾼다. */
    public void approve(LocalDateTime reviewedAt) {
        this.status = RefundStatus.APPROVED;
        this.reviewedAt = reviewedAt;
    }

    /** 거절(REFUND-002). */
    public void reject(String rejectionReason, LocalDateTime reviewedAt) {
        this.status = RefundStatus.REJECTED;
        this.rejectionReason = rejectionReason;
        this.reviewedAt = reviewedAt;
    }

    public boolean isRequested() {
        return status == RefundStatus.REQUESTED;
    }
}