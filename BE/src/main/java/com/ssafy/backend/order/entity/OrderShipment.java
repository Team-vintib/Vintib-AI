package com.ssafy.backend.order.entity;

import jakarta.persistence.CheckConstraint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
 * 주문 배송지·송장 정보. {@code PointAccount}와 같은 공유 PK 1:1
 * 구조 — 주문당 한 행만 존재한다. 배송지(recipient*)는 구매자가, 송장(courier/trackingNumber)은
 * 판매자가 채운다.
 *
 * <p>배송완료(deliveredAt)는 웹훅으로 실제 배송완료 신호를 받았을 때만 {@link #markDelivered}가 채운다.
 */
@Entity
@Table(
        name = "order_shipment",
        check = {
                @CheckConstraint(
                        name = "ck_order_shipment_courier",
                        constraint = "courier IN ("
                                + "'LOTTE', 'CJ', 'HANJIN', 'POST', 'KYUNGDONG', "
                                + "'DAESIN', 'LOGEN', 'HAPDONG', 'COUPANG', 'WOORI')"),
                @CheckConstraint(
                        name = "ck_order_shipment_tracking_status",
                        constraint = "tracking_status IN ("
                                + "'PENDING', 'REGISTERED', 'PICKUP_READY', 'PICKED_UP', 'IN_TRANSIT', "
                                + "'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'RETURNED', 'CANCELLED', "
                                + "'HOLD', 'UNKNOWN')")
        })
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

    @Enumerated(EnumType.STRING)
    @Column(length = 50)
    private CourierCode courier;

    @Column(name = "tracking_number", length = 50)
    private String trackingNumber;

    @Column(name = "shipped_at")
    private LocalDateTime shippedAt;

    @Column(name = "delivered_at")
    private LocalDateTime deliveredAt;

    /** 배송 진행 상태. 송장 등록 직후 첫 웹훅을 받기 전에는 null. */
    @Enumerated(EnumType.STRING)
    @Column(name = "tracking_status", length = 20)
    private TrackingStatus trackingStatus;

    /**
     * 배송 조회 웹훅 구독 성공 여부. 실패 건(자격증명 없는 로컬/CI 환경 등)만
     * {@link com.ssafy.backend.order.scheduler.ShipmentFallbackDeliveryScheduler}가 지연 폴백 대상으로
     * 집어간다 — {@code trackingStatus}만으로는 "웹훅 구독은 됐지만 첫 웹훅 전"과 "폴백 대상"을 구분할
     * 수 없어(둘 다 null) 별도로 둔다.
     */
    @Column(name = "webhook_subscribed", nullable = false)
    private boolean webhookSubscribed;

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

    /** 배송지 등록/수정. 송장이 등록되기 전까지만 서비스가 호출을 허용한다. */
    public void updateAddress(String recipientName, String recipientPhone, String zipcode, String address1, String address2) {
        this.recipientName = recipientName;
        this.recipientPhone = recipientPhone;
        this.zipcode = zipcode;
        this.address1 = address1;
        this.address2 = address2;
    }

    /** 송장 등록. 배송완료는 아직 모른다 — 웹훅으로만 {@link #markDelivered}가 채운다. */
    public void registerTracking(CourierCode courier, String trackingNumber, LocalDateTime shippedAt) {
        this.courier = courier;
        this.trackingNumber = trackingNumber;
        this.shippedAt = shippedAt;
    }

    /** 배송완료 웹훅 수신 또는 지연 폴백 배치(구독 실패 건)에서 호출한다. */
    public void markDelivered(LocalDateTime deliveredAt) {
        this.deliveredAt = deliveredAt;
    }

    /** 배송 조회 웹훅 구독 결과 저장. 실패(false)면 지연 폴백 배치의 대상이 된다. */
    public void markWebhookSubscribed(boolean webhookSubscribed) {
        this.webhookSubscribed = webhookSubscribed;
    }

    /**
     * 배송 진행 상태 갱신. 웹훅이 올 때마다(상태가 무엇이든) 호출된다 —
     * {@link #markDelivered}와 별개로, 구매자가 진행 상황을 볼 수 있게 하기 위함이다.
     */
    public void updateTrackingStatus(TrackingStatus trackingStatus) {
        this.trackingStatus = trackingStatus;
    }
}