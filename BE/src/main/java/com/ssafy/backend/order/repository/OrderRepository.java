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

    /** 마이페이지 요약 — 구매 건수. */
    long countByBuyer_Id(Long buyerId);

    /** 마이페이지 요약 — 판매 건수. */
    long countBySeller_Id(Long sellerId);

    /**
     * 자동 구매 확정 배치 대상 조회(ORDER-003) — {@code ix_orders_auto_confirm} 부분 인덱스를 탄다.
     * 환불 요청이 진행 중인 주문은 제외한다 — 배치가 한 건이라도 예외를 던지면 트랜잭션 전체가
     * 롤백돼 나머지 정상 주문까지 실패하므로, 쿼리 단계에서 걸러낸다({@code RefundService} 참고).
     */
    List<Order> findByStatusAndAutoConfirmAtLessThanEqualAndRefundRequestedFalse(OrderStatus status, LocalDateTime now);
}