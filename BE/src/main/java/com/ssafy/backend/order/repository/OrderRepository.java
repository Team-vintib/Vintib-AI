package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrderRepository extends JpaRepository<Order, Long> {

    /** 마이페이지 구매/낙찰 내역 조회(MY-003). */
    Page<Order> findByBuyer_IdOrderByCreatedAtDesc(Long buyerId, Pageable pageable);

    /** 마이페이지 판매/정산 내역 조회(MY-004). */
    Page<Order> findBySeller_IdOrderByCreatedAtDesc(Long sellerId, Pageable pageable);

    /** 마이페이지 요약 — 구매 건수. */
    long countByBuyer_Id(Long buyerId);

    /** 데모 주문 시드(DemoOrderSeeder) — 구매자 기준 상태별 건수. 상태 버킷별 목표치를 채울 때 쓴다. */
    long countByBuyer_IdAndStatus(Long buyerId, OrderStatus status);

    /** 마이페이지 요약 — 판매 건수. */
    long countBySeller_Id(Long sellerId);

    /** 데모 주문 시드(DemoOrderSeeder) — 판매자에게 특정 상태 주문이 이미 있는지(멱등 체크). */
    boolean existsBySeller_IdAndStatus(Long sellerId, OrderStatus status);

    /**
     * 자동 구매 확정 배치 대상 조회(ORDER-003) — {@code ix_orders_auto_confirm} 부분 인덱스를 탄다.
     * 환불 요청이 진행 중인 주문은 제외한다 — 배치가 한 건이라도 예외를 던지면 트랜잭션 전체가
     * 롤백돼 나머지 정상 주문까지 실패하므로, 쿼리 단계에서 걸러낸다({@code RefundService} 참고).
     */
    List<Order> findByStatusAndAutoConfirmAtLessThanEqualAndRefundRequestedFalse(OrderStatus status, LocalDateTime now);

    /**
     * 방송 종료 요약(LIVE-006)의 즉시구매분 — 이 방송에서 <b>경매를 거치지 않고</b> 팔린 주문.
     *
     * <p>{@code auction IS NULL}로 낙찰 주문을 뺀다. 낙찰분은 경매 쪽에서 이미 집계하므로 여기까지
     * 세면 같은 상품이 두 번 잡힌다.
     *
     * <p>환불된 주문은 뺀다 — 돌려준 돈을 방송 판매액에 남겨 둘 이유가 없다. 배송 중·구매 확정
     * 등 진행 단계는 구분하지 않는다(팔린 것은 팔린 것이다).
     */
    @Query("""
            SELECT o FROM Order o
            WHERE o.live.id = :liveId
              AND o.auction IS NULL
              AND o.status <> com.ssafy.backend.order.entity.OrderStatus.REFUNDED
              AND o.status <> com.ssafy.backend.order.entity.OrderStatus.CANCELED
            """)
    List<Order> findLiveDirectSaleOrders(@Param("liveId") Long liveId);
}