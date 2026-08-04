package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {

    /** 마이페이지 구매/낙찰 내역 조회(MY-003). */
    Page<Order> findByBuyer_IdOrderByCreatedAtDesc(Long buyerId, Pageable pageable);

    /** 마이페이지 판매/정산 내역 조회(MY-004). */
    Page<Order> findBySeller_IdOrderByCreatedAtDesc(Long sellerId, Pageable pageable);

    /** 마이페이지 요약(에픽 S15P11A108-207 보너스) — 구매 건수. */
    long countByBuyer_Id(Long buyerId);

    /** 마이페이지 요약(에픽 S15P11A108-207 보너스) — 판매 건수. */
    long countBySeller_Id(Long sellerId);

    /** 자동 구매 확정 배치 대상 조회(ORDER-003) — {@code ix_orders_auto_confirm} 부분 인덱스를 탄다. */
    List<Order> findByStatusAndAutoConfirmAtLessThanEqual(OrderStatus status, LocalDateTime now);
}
