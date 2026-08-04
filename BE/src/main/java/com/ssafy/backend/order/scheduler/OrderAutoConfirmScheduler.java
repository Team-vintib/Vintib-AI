package com.ssafy.backend.order.scheduler;

import com.ssafy.backend.order.service.OrderService;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 자동 구매 확정 배치(ORDER-003). 배송 완료(DELIVERED) 후 7일이 지난 주문을 찾아
 * {@link OrderService#autoConfirmDueOrders}로 구매 확정과 동일하게 정산한다.
 *
 * <p>주기는 운영 정책이 미확정이라 10분으로 잡는다 — 정책이 정해지면 조정한다.
 */
@Component
@RequiredArgsConstructor
public class OrderAutoConfirmScheduler {

    private static final long FIXED_DELAY_MS = 10 * 60 * 1000L;

    private final OrderService orderService;

    @Scheduled(fixedDelay = FIXED_DELAY_MS)
    public void autoConfirmDueOrders() {
        orderService.autoConfirmDueOrders();
    }
}
