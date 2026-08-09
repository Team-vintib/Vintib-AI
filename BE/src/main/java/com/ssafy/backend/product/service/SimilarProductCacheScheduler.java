package com.ssafy.backend.product.service;

import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 유사 상품 캐시 배치 갱신(CH034). 노출 대상 상품마다 {@link SimilarProductCacheService}로
 * AI 유사 상품 후보를 미리 계산해 캐시에 채운다 — 상품 상세 조회(서빙 경로)는 이 캐시만 읽고
 * AI를 직접 호출하지 않는다.
 *
 * <p><b>다른 스케줄러(전부 {@code fixedDelay}, 수십 초~수 분 간격 폴링)와 달리 여기는
 * {@code cron}을 쓴다</b> — 이건 폴링이 아니라 트래픽이 적은 특정 시각(새벽)에 몰아서 도는
 * 배치라 시각 지정이 필요하다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SimilarProductCacheScheduler {

    // DRAFT(미공개)는 애초에 노출되지 않으니 캐시가 필요 없다. SOLD는 배치 대상에서 빼되
    // (판매 종료 상품의 캐시를 갱신할 실익이 낮다), 이미 계산돼 있던 캐시가 남아 있어도
    // 서빙 시점의 실시간 판매상태 필터링이 걸러낸다.
    private static final List<SaleStatus> ELIGIBLE_STATUSES =
            List.of(SaleStatus.ON_SALE, SaleStatus.AUCTION_SCHEDULED, SaleStatus.AUCTION_IN_PROGRESS);

    private final ProductRepository productRepository;
    private final SimilarProductCacheService cacheService;

    /** 매일 새벽 3시(트래픽이 적은 시간대) 1회. */
    @Scheduled(cron = "0 0 3 * * *")
    public void refreshAll() {
        List<Long> productIds = productRepository.findIdsBySaleStatusIn(ELIGIBLE_STATUSES);
        log.info("유사 상품 캐시 배치 시작 - 대상 {}건", productIds.size());

        int succeeded = 0;
        for (Long productId : productIds) {
            try {
                cacheService.refreshCache(productId);
                succeeded++;
            } catch (Exception e) {
                // 상품 하나의 실패가 배치 전체를 멈추면 안 된다. 다음 배치 때 다시 시도한다.
                log.warn("상품 {} 유사 상품 캐시 갱신 중 예외 - 스킵", productId, e);
            }
        }
        log.info("유사 상품 캐시 배치 종료 - 성공 {}/{}건", succeeded, productIds.size());
    }
}
