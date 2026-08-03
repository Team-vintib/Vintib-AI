package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {
}
