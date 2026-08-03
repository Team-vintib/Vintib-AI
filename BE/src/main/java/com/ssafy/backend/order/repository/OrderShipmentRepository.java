package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.OrderShipment;
import org.springframework.data.jpa.repository.JpaRepository;

// PK가 order_id 그대로라 findById(orderId)로 바로 조회된다 — 별도 파생 쿼리가 필요 없다.
public interface OrderShipmentRepository extends JpaRepository<OrderShipment, Long> {
}
