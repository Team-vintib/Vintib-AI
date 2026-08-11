package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.OrderShipment;
import com.ssafy.backend.order.entity.OrderStatus;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

// PK가 order_id 그대로라 findById(orderId)로 바로 조회된다.
public interface OrderShipmentRepository extends JpaRepository<OrderShipment, Long> {

    /** 배송 조회 웹훅 수신(SHIP-002) — (택배사, 송장번호)로 대상 주문을 역으로 찾는다. */
    Optional<OrderShipment> findByCourierAndTrackingNumber(CourierCode courier, String trackingNumber);

    /** 지연 폴백 배치 대상 조회 — 웹훅 구독에 실패해 진행 상태를 알 방법이 없는 배송 중 건. */
    List<OrderShipment> findByOrder_StatusAndWebhookSubscribedFalseAndShippedAtLessThanEqual(
            OrderStatus status, LocalDateTime shippedAtCutoff);
}
