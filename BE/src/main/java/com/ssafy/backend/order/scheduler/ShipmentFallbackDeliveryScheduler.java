package com.ssafy.backend.order.scheduler;

import com.ssafy.backend.order.service.OrderService;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 배송 조회 웹훅 구독 실패 건의 지연 폴백 배치. {@link OrderService#deliverDueFallbackShipments}로
 * 송장 등록 후 {@code OrderService.FALLBACK_DELAY}가 지난 건을 찾아 배송완료 처리한다.
 *
 * <p>기존에는 웹훅 구독 실패 시 송장 등록과 동시에 즉시 배송완료 처리했는데(등록 시각이 그대로
 * {@code deliveredAt}이 되는 문제), 이 배치가 그 즉시-확정을 대체한다 — 최소한의 시간 지연을 두고
 * 배치 실행 시각을 {@code deliveredAt}으로 기록해 "등록 시각 = 완료 시각"이던 문제를 없앤다.
 *
 * <p>주기는 {@link OrderAutoConfirmScheduler}와 마찬가지로 운영 정책 미확정이라 짧게(1분) 잡는다.
 */
@Component
@RequiredArgsConstructor
public class ShipmentFallbackDeliveryScheduler {

    private static final long FIXED_DELAY_MS = 60 * 1000L;

    private final OrderService orderService;

    @Scheduled(fixedDelay = FIXED_DELAY_MS)
    public void deliverDueFallbackShipments() {
        orderService.deliverDueFallbackShipments();
    }
}
