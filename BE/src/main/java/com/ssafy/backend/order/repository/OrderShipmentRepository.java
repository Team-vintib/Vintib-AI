package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.OrderShipment;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

// PK가 order_id 그대로라 findById(orderId)로 바로 조회된다.
public interface OrderShipmentRepository extends JpaRepository<OrderShipment, Long> {

    /** 배송 조회 웹훅 수신(SHIP-002) — (택배사, 송장번호)로 대상 주문을 역으로 찾는다. */
    Optional<OrderShipment> findByCourierAndTrackingNumber(CourierCode courier, String trackingNumber);
}
