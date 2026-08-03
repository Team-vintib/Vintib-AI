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
 * <p>생성은 {@link #createDirectSale}(SALE-002, 상시 판매 즉시구매)로만 한다 — 경매 낙찰(AUCT)
 * 주문은 입찰 자체가 아직 없어 이번 범위에서 다루지 않는다({@code auction}은 항상 NULL).
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

    /** 상시 판매 즉시구매 주문 생성(SALE-002). 결제(포인트 보관)는 서비스가 처리하고, 이 주문은 항상 PAID로 시작한다. */
    public static Order createDirectSale(Member buyer, Member seller, Product product, Long orderPrice) {
        return new Order(buyer, seller, product, null, orderPrice, OrderStatus.PAID);
    }

    /** memberId가 이 주문의 구매자 또는 판매자인지 확인한다. 세금계산서 등 주문 관련 API의 권한 확인에 쓴다. */
    public boolean isPartyOf(Long memberId) {
        return memberId != null && (buyer.getId().equals(memberId) || seller.getId().equals(memberId));
    }

    public boolean isBuyer(Long memberId) {
        return memberId != null && buyer.getId().equals(memberId);
    }
}
