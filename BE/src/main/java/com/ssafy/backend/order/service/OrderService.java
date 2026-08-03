package com.ssafy.backend.order.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.dto.request.OrderCreateRequest;
import com.ssafy.backend.order.dto.request.OrderRole;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 주문 조회(MY-003/004), 상시 판매 주문 생성(SALE-002). 세금계산서 발행은 {@code InvoiceService}가 담당한다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final PointService pointService;

    /**
     * {@code role}로 구매자/판매자 관점을 구분해 본인 주문 목록을 최신순으로 조회한다(MY-003/004).
     * 정산 완료 여부는 {@code order.status}가 SETTLED인지로 판단하며, 정산액은 수수료 없이
     * orderPrice 그대로다.
     */
    public PageResponse<OrderListItemResponse> getOrders(Long memberId, OrderRole role, Pageable pageable) {
        Page<Order> orders = role == OrderRole.BUYER
                ? orderRepository.findByBuyer_IdOrderByCreatedAtDesc(memberId, pageable)
                : orderRepository.findBySeller_IdOrderByCreatedAtDesc(memberId, pageable);
        return PageResponse.from(orders.map(OrderListItemResponse::from));
    }

    /** 주문 상세 조회(MY-003). 경로에 userId가 없어 order.isPartyOf(principal)로 권한을 확인한다. */
    public OrderListItemResponse getOrderDetail(Long orderId, Long memberId) {
        return OrderListItemResponse.from(findOrder(orderId, memberId));
    }

    /**
     * 상시 판매 즉시구매(SALE-002). 결제(포인트 보관), 주문 생성, 상품 SOLD 처리를 한 트랜잭션으로 묶는다.
     * 결제는 {@link PointService#pay}가 처리하며 잔액 부족이면 여기서 예외가 전파돼 전체가 롤백된다.
     */
    @Transactional
    public OrderListItemResponse createOrder(Long buyerId, OrderCreateRequest request) {
        Product product = productRepository.findById(request.productId())
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));
        if (!product.isAvailableForDirectPurchase()) {
            throw new CustomException(ErrorCode.PRODUCT_NOT_AVAILABLE_FOR_PURCHASE);
        }
        if (product.isOwnedBy(buyerId)) {
            throw new CustomException(ErrorCode.SELF_PURCHASE_NOT_ALLOWED);
        }

        Member buyer = memberRepository.findById(buyerId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        Order order = orderRepository.save(
                Order.createDirectSale(buyer, product.getSeller(), product, product.getPrice()));

        pointService.pay(buyerId, product.getPrice(), order.getId());
        product.markSold();

        return OrderListItemResponse.from(order);
    }

    private Order findOrder(Long orderId, Long memberId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_NOT_FOUND));
        if (!order.isPartyOf(memberId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }
        return order;
    }
}
