package com.ssafy.backend.product.service;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * {@link SimilarProductCacheScheduler} 단위 테스트(CH034). 상품 하나가 실패해도 나머지는 계속
 * 갱신되는 격리(다른 스케줄러 테스트와 같은 관례, {@code ChatAnswerPollingSchedulerTest})를 본다.
 */
@ExtendWith(MockitoExtension.class)
class SimilarProductCacheSchedulerTest {

    @Mock
    private ProductRepository productRepository;

    @Mock
    private SimilarProductCacheService cacheService;

    private SimilarProductCacheScheduler scheduler;

    private void setUp() {
        scheduler = new SimilarProductCacheScheduler(productRepository, cacheService);
    }

    @Test
    void 대상_상품마다_캐시_갱신을_호출한다() {
        setUp();
        when(productRepository.findIdsBySaleStatusIn(
                        List.of(SaleStatus.ON_SALE, SaleStatus.AUCTION_SCHEDULED, SaleStatus.AUCTION_IN_PROGRESS)))
                .thenReturn(List.of(1L, 2L));

        scheduler.refreshAll();

        verify(cacheService).refreshCache(1L);
        verify(cacheService).refreshCache(2L);
    }

    @Test
    void 한_상품이_실패해도_나머지_상품은_계속_갱신된다() {
        setUp();
        when(productRepository.findIdsBySaleStatusIn(
                        List.of(SaleStatus.ON_SALE, SaleStatus.AUCTION_SCHEDULED, SaleStatus.AUCTION_IN_PROGRESS)))
                .thenReturn(List.of(1L, 2L));
        org.mockito.Mockito.doThrow(new RuntimeException("db error"))
                .when(cacheService).refreshCache(eq(1L));

        scheduler.refreshAll();

        verify(cacheService, times(1)).refreshCache(2L);
    }
}
