package com.ssafy.backend.order.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.order.dto.request.OrderRole;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 마이페이지 구매/낙찰 내역(MY-003)·판매/정산 내역(MY-004) 조회. 발행 처리는 {@link InvoiceService}가 담당한다. */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orderRepository;

    /**
     * {@code role}로 구매자/판매자 관점을 구분해 본인 주문 목록을 최신순으로 조회한다(MY-003/004).
     * 판매/정산 관점(SELLER)에서 "정산" 자체는 수수료 계산이나 실제 정산 트리거가 없어,
     * {@code order.status}가 SETTLED인지 여부로만 판단하고 정산액은 orderPrice 그대로 쓴다.
     */
    public PageResponse<OrderListItemResponse> getOrders(Long memberId, OrderRole role, Pageable pageable) {
        Page<Order> orders = role == OrderRole.BUYER
                ? orderRepository.findByBuyer_IdOrderByCreatedAtDesc(memberId, pageable)
                : orderRepository.findBySeller_IdOrderByCreatedAtDesc(memberId, pageable);
        return PageResponse.from(orders.map(OrderListItemResponse::from));
    }

    /** 주문 상세 조회(MY-003). 경로에 userId가 없어 order.isPartyOf(principal)로 권한을 확인한다. */
    public OrderListItemResponse getOrderDetail(Long orderId, Long memberId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_NOT_FOUND));
        if (!order.isPartyOf(memberId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }
        return OrderListItemResponse.from(order);
    }
}
