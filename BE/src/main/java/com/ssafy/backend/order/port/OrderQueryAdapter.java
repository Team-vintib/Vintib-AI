package com.ssafy.backend.order.port;

import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.product.port.OrderQueryPort;
import com.ssafy.backend.product.port.dto.CompletedOrderSummary;
import java.util.Collection;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class OrderQueryAdapter implements OrderQueryPort {

    private final OrderRepository orderRepository;

    @Override
    public List<CompletedOrderSummary> findCompletedOrders(Collection<Long> productIds) {
        return orderRepository.findByProductIdIn(productIds).stream()
                .map(order -> CompletedOrderSummary.builder()
                        .productId(order.getProduct().getId())
                        .orderPrice(order.getOrderPrice())
                        .auctionWin(order.getAuction() != null)
                        .build())
                .toList();
    }
}
