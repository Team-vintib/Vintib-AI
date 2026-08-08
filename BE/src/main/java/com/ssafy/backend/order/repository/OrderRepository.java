package com.ssafy.backend.order.repository;

import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import java.time.LocalDateTime;
import java.util.Collection;
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

    /** 마이페이지 요약 — 판매 건수. */
    long countBySeller_Id(Long sellerId);

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

    /**
     * "동일 상품 시세"(CH001, 047)의 완료거래가 배치 조회 — 여러 상품 id를 한 번에 조회해
     * {@code AuctionRepository.findByProductIdIn}과 같은 이유로 N+1을 피한다.
     *
     * <p>재고 1개짜리 세컨핸드 상품이라 정상적으로는 상품당 완료 주문이 최대 1건이지만,
     * 환불 후 재판매 등 예외적으로 여러 건이 남을 수 있어 List로 받는다 — 호출부가 상품
     * id별로 필요한 걸 고른다. 환불·취소된 주문은 뺀다({@code findLiveDirectSaleOrders}와
     * 같은 이유 — 완결되지 않은 거래를 시세 근거로 쓰면 안 된다). {@code auction IS NULL}
     * 여부로 직접판매/경매낙찰을 구분한다.
     */
    @Query("""
            SELECT o FROM Order o
            WHERE o.product.id IN :productIds
              AND o.status <> com.ssafy.backend.order.entity.OrderStatus.REFUNDED
              AND o.status <> com.ssafy.backend.order.entity.OrderStatus.CANCELED
            """)
    List<Order> findByProductIdIn(@Param("productIds") Collection<Long> productIds);
}