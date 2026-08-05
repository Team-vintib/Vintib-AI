package com.ssafy.backend.live.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
 * 라이브에 걸린 상품(LIVE-003). 방송 전·중 모두 추가·제외할 수 있고 개수 제한은 없다.
 *
 * <p><b>제외는 물리 삭제가 아니라 {@code removedAt} 기록이다.</b> 방송 중 제외했더라도
 * "그 시점에 연결돼 있었다"는 사실이 남아야 다시보기 타임라인(LIVE-008)을 만들 수 있다
 * (erd.md §6). 같은 상품을 같은 라이브에 중복 연결하는 것은 부분 UNIQUE 인덱스
 * {@code ux_live_product_active}(제외된 건은 재연결 허용)가 DB에서 막는다 — JPA로는
 * 표현할 수 없는 형태라 DDL이 소유한다.
 *
 * <p>상품은 연관관계 대신 식별자로 들고 있는다. 라이브가 상품 도메인을 직접 참조하지 않고
 * {@code ProductQueryPort}만 거치도록 경계를 지키기 위함이다.
 */
@Entity
@Table(name = "live_product")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LiveProduct {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "live_id", nullable = false)
    private Live live;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "sort_order", nullable = false)
    private Short sortOrder;

    @Column(name = "added_at", nullable = false)
    private LocalDateTime addedAt;

    /** 제외 시각. null이면 현재 연결 중이다. */
    @Column(name = "removed_at")
    private LocalDateTime removedAt;

    private LiveProduct(Live live, Long productId, Short sortOrder, LocalDateTime addedAt) {
        this.live = live;
        this.productId = productId;
        this.sortOrder = sortOrder;
        this.addedAt = addedAt;
    }

    /** 라이브에 상품을 연결한다. */
    public static LiveProduct link(Live live, Long productId, Short sortOrder, LocalDateTime addedAt) {
        return new LiveProduct(live, productId, sortOrder, addedAt);
    }

    /** 연결을 해제한다(물리 삭제 대신 제외 시각 기록). */
    public void unlink(LocalDateTime removedAt) {
        this.removedAt = removedAt;
    }

    public boolean isLinked() {
        return removedAt == null;
    }
}
