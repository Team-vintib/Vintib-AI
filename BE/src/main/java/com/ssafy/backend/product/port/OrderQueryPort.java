package com.ssafy.backend.product.port;

import com.ssafy.backend.product.port.dto.CompletedOrderSummary;
import java.util.Collection;
import java.util.List;

public interface OrderQueryPort {

    /** 상품 id 목록의 완료(환불·취소 제외)거래를 배치 조회한다("동일 상품 시세", CH001). */
    List<CompletedOrderSummary> findCompletedOrders(Collection<Long> productIds);
}
