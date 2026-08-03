package com.ssafy.backend.order.entity;

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
 * 주문 배송지·송장 정보(ORDER-001, SHIP-001/002). {@code PointAccount}와 같은 공유 PK 1:1
 * 구조 — 주문당 한 행만 존재한다. 배송지(recipient*)는 구매자가, 송장(courier/trackingNumber)은
 * 판매자가 채운다.
 */
@Entity
@Table(name = "order_shipment")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OrderShipment {

    @Id
    private Long orderId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id")
    private Order order;

    @Column(name = "recipient_name", nullable = false, length = 50)
    private String recipientName;

    @Column(name = "recipient_phone", nullable = false, length = 20)
    private String recipientPhone;

    @Column(nullable = false, length = 10)
    private String zipcode;

    @Column(nullable = false, length = 255)
    private String address1;

    @Column(length = 255)
    private String address2;

    @Column(length = 50)
    private String courier;

    @Column(name = "tracking_number", length = 50)
    private String trackingNumber;

    @Column(name = "shipped_at")
    private LocalDateTime shippedAt;

    @Column(name = "delivered_at")
    private LocalDateTime deliveredAt;

    @Builder
    private OrderShipment(
            Order order, String recipientName, String recipientPhone, String zipcode, String address1,
            String address2) {
        this.order = order;
        this.recipientName = recipientName;
        this.recipientPhone = recipientPhone;
        this.zipcode = zipcode;
        this.address1 = address1;
        this.address2 = address2;
    }

    /** 배송지 등록/수정(ORDER-001). 송장이 등록되기 전까지만 서비스가 호출을 허용한다. */
    public void updateAddress(String recipientName, String recipientPhone, String zipcode, String address1, String address2) {
        this.recipientName = recipientName;
        this.recipientPhone = recipientPhone;
        this.zipcode = zipcode;
        this.address1 = address1;
        this.address2 = address2;
    }

    /**
     * 송장 등록(SHIP-001). 실제 택배 연동이 없어 등록 시점에 배송 시작·완료를 함께 기록한다
     * ({@code Order#markDelivered} 참고).
     */
    public void registerTracking(String courier, String trackingNumber, LocalDateTime shippedAt, LocalDateTime deliveredAt) {
        this.courier = courier;
        this.trackingNumber = trackingNumber;
        this.shippedAt = shippedAt;
        this.deliveredAt = deliveredAt;
    }
}
