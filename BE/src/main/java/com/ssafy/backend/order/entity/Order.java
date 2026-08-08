package com.ssafy.backend.order.entity;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.live.entity.Live;
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
 * <p>생성 경로는 둘이다 — {@link #createDirectSale}(SALE-002, 상시 판매 즉시구매, {@code auction}이
 * NULL)과 {@link #createAuctionWin}(AUCT-012, 경매 낙찰). 후자는 경매 마감 스케줄러가 부르며
 * 구매자의 결제 동작 없이 만들어진다 — 이유는 그 메서드 주석 참고.
 * 상태 전이 메서드는 전제조건을 검증하지 않는다 — 검증은 {@code OrderService}가 한다
 * (다른 엔티티의 상태 전이와 같은 패턴).
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

    /**
     * 이 주문이 발생한 방송(LIVE-006 방송 종료 요약). <b>라이브 밖에서 산 주문은 NULL이다.</b>
     *
     * <p><b>경매 낙찰이면 {@code auction.live}로 알 수 있는데도 따로 두는 이유.</b> 라이브 중
     * 즉시구매는 경매를 거치지 않아 방송과 이을 근거가 아예 없다. 두 경로를 한 컬럼으로 묶어야
     * "이 방송에서 발생한 주문"을 조건 하나로 뽑을 수 있다.
     *
     * <p>낙찰 주문에도 채운다 — 파생 가능하다고 비워 두면 같은 질문에 답이 두 갈래가 된다.
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "live_id")
    private Live live;

    @Column(name = "order_price", nullable = false)
    private Long orderPrice;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private OrderStatus status;

    @Column(name = "auto_confirm_at")
    private LocalDateTime autoConfirmAt;

    /** 정산 완료 시각(SETTLED로 전이한 시점) — {@code SETTLED}가 아닌 주문은 항상 {@code null}이다. */
    @Column(name = "settled_at")
    private LocalDateTime settledAt;

    @Column(name = "refund_requested", nullable = false)
    private boolean refundRequested;

    @Builder(access = AccessLevel.PACKAGE)
    private Order(
            Member buyer,
            Member seller,
            Product product,
            Auction auction,
            Live live,
            Long orderPrice,
            OrderStatus status) {
        this.buyer = buyer;
        this.seller = seller;
        this.product = product;
        this.auction = auction;
        this.live = live;
        this.orderPrice = orderPrice;
        this.status = status == null ? OrderStatus.PAID : status;
    }

    /**
     * 상시 판매 즉시구매 주문 생성(SALE-002). 결제(포인트 보관)는 서비스가 처리하고, 이 주문은
     * 항상 PAID로 시작한다.
     *
     * @param live 라이브 시청 화면에서 산 경우 그 방송. <b>라이브 밖에서 샀으면 {@code null}</b> —
     *             방송 종료 요약(LIVE-006)이 이 값으로 방송 실적을 집계한다
     */
    public static Order createDirectSale(
            Member buyer, Member seller, Product product, Live live, Long orderPrice) {
        return new Order(buyer, seller, product, null, live, orderPrice, OrderStatus.PAID);
    }

    /**
     * 경매 낙찰 주문 생성(AUCT-012, 정윤 추가 — JY008 설계 판단 12).
     *
     * <p>즉시구매와 달리 <b>구매자가 결제 버튼을 누르는 시점이 없다.</b> 입찰한 순간 낙찰 시
     * 구매 의무가 확정되고 그 금액이 이미 보류돼 있어서, 마감과 동시에 주문이 만들어지고
     * 보류가 거래 대금으로 전환된다({@code PointCommandPort.convertHoldToPayment}).
     * 그래서 여기서도 {@code PAID}로 시작하며, 이후 배송·구매확정은 즉시구매와 완전히 같은
     * 흐름을 탄다.
     *
     * <p>방송은 경매에서 따라 나오므로 따로 받지 않는다.
     */
    public static Order createAuctionWin(
            Member buyer, Member seller, Product product, Auction auction, Long finalPrice) {
        return new Order(
                buyer, seller, product, auction, auction.getLive(), finalPrice, OrderStatus.PAID);
    }

    /** 송장 등록(SHIP-001). 전제조건(PAID 상태)은 서비스가 검증한다. */
    public void markShipping() {
        this.status = OrderStatus.SHIPPING;
    }

    /**
     * 배송 완료 처리 — 이번 범위에서는 실제 택배 연동이 없어 송장 등록과 같은 시점에 호출된다
     * ({@code OrderService} 참고). 자동 구매 확정 시각을 여기서 계산해 채운다.
     */
    public void markDelivered(LocalDateTime deliveredAt) {
        this.status = OrderStatus.DELIVERED;
        this.autoConfirmAt = deliveredAt.plusDays(3);
    }

    /**
     * 구매 확정 처리(ORDER-002/003). 전제조건(DELIVERED 상태)은 서비스가 검증한다.
     * 정산 대기 절차가 없어 CONFIRMED를 거쳐 곧바로 SETTLED로 끝난다.
     */
    public void confirmAndSettle(LocalDateTime settledAt) {
        this.status = OrderStatus.CONFIRMED;
        this.status = OrderStatus.SETTLED;
        this.settledAt = settledAt;
    }

    /** 환불 요청(REFUND-001) — 전제조건(PAID/SHIPPING/DELIVERED, 중복 요청 아님)은 서비스가 검증한다. */
    public void markRefundRequested() {
        this.refundRequested = true;
    }

    /**
     * 환불 승인(REFUND-002) — {@code status}를 바꾸지 않고 바로 REFUNDED로 전이한다.
     * 정산(포인트 환급)은 서비스가 처리한다.
     */
    public void markRefunded() {
        this.refundRequested = false;
        this.status = OrderStatus.REFUNDED;
    }

    /** 환불 거절(REFUND-002) — {@code status}는 요청 이전 상태 그대로 둔다(진행 중이던 흐름을 이어간다). */
    public void clearRefundRequested() {
        this.refundRequested = false;
    }

    /** memberId가 이 주문의 구매자 또는 판매자인지 확인한다. 세금계산서 등 주문 관련 API의 권한 확인에 쓴다. */
    public boolean isPartyOf(Long memberId) {
        return memberId != null && (buyer.getId().equals(memberId) || seller.getId().equals(memberId));
    }

    public boolean isBuyer(Long memberId) {
        return memberId != null && buyer.getId().equals(memberId);
    }

    public boolean isSeller(Long memberId) {
        return memberId != null && seller.getId().equals(memberId);
    }
}