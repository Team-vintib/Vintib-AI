package com.ssafy.backend.order.entity;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
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
 * 주문. 스키마는 {@code docs/db/schema.sql}의 {@code orders} 테이블이 단일 기준이다.
 *
 * <p>이번 범위(BIZ-002)에는 주문 생성 API가 없다 — 세금계산서가 FK로 참조할 대상으로만
 * 필요해 엔티티·조회 레포지토리만 둔다. 그래서 빌더를 패키지 전용으로 막아 외부에서
 * 함부로 생성하지 못하게 한다(테스트 시딩은 SQL 직접 삽입 또는 같은 패키지 테스트에서만 사용).
 */
@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "buyer_id", nullable = false)
    private Member buyer;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "seller_id", nullable = false)
    private Member seller;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "auction_id")
    private Auction auction;

    @Column(name = "order_price", nullable = false)
    private Long orderPrice;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private OrderStatus status;

    @Column(name = "auto_confirm_at")
    private LocalDateTime autoConfirmAt;

    @Builder(access = AccessLevel.PACKAGE)
    private Order(Member buyer, Member seller, Product product, Auction auction, Long orderPrice, OrderStatus status) {
        this.buyer = buyer;
        this.seller = seller;
        this.product = product;
        this.auction = auction;
        this.orderPrice = orderPrice;
        this.status = status == null ? OrderStatus.PAID : status;
    }

    /** memberId가 이 주문의 구매자 또는 판매자인지 확인한다. 세금계산서 등 주문 관련 API의 권한 확인에 쓴다. */
    public boolean isPartyOf(Long memberId) {
        return memberId != null && (buyer.getId().equals(memberId) || seller.getId().equals(memberId));
    }
}
