package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {

    /** 마이페이지 구매/낙찰 내역 조회(MY-003). */
    Page<Order> findByBuyer_IdOrderByCreatedAtDesc(Long buyerId, Pageable pageable);

    /** 마이페이지 판매/정산 내역 조회(MY-004). */
    Page<Order> findBySeller_IdOrderByCreatedAtDesc(Long sellerId, Pageable pageable);
}
