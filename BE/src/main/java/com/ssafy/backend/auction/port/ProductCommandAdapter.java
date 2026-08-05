package com.ssafy.backend.auction.port;

import com.ssafy.backend.product.entity.SaleStatus;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/** {@link ProductCommandPort}의 유일한 구현. 상품 도메인에 대한 의존을 이 파일 하나로 묶는다. */
@Component
@RequiredArgsConstructor
public class ProductCommandAdapter implements ProductCommandPort {

    private final ProductSaleStatusRepository productSaleStatusRepository;

    @Override
    public int markAuctionScheduled(Long productId) {
        return productSaleStatusRepository.updateSaleStatus(productId, SaleStatus.AUCTION_SCHEDULED);
    }

    @Override
    public int markAuctionInProgress(Long productId) {
        return productSaleStatusRepository.updateSaleStatus(productId, SaleStatus.AUCTION_IN_PROGRESS);
    }

    @Override
    public int markSold(Long productId) {
        return productSaleStatusRepository.updateSaleStatus(productId, SaleStatus.SOLD);
    }
}
