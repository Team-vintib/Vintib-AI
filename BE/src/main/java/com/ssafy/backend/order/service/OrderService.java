package com.ssafy.backend.order.service;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.dto.request.OrderCreateRequest;
import com.ssafy.backend.order.dto.request.OrderRole;
import com.ssafy.backend.order.dto.request.OrderShipmentAddressRequest;
import com.ssafy.backend.order.dto.request.OrderShipmentRegisterRequest;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.dto.response.OrderShipmentResponse;
import com.ssafy.backend.order.entity.CourierCode;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderShipment;
import com.ssafy.backend.order.entity.OrderStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.order.repository.OrderShipmentRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 주문 조회(MY-003/004), 상시 판매 주문 생성(SALE-002), 배송지·송장(ORDER-001, SHIP-001/002),
 * 구매 확정·정산(ORDER-002/003, {@link #confirmOrder}/{@link #autoConfirmDueOrders}).
 * 세금계산서 발행은 {@code InvoiceService}가 담당한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orderRepository;
    private final OrderShipmentRepository orderShipmentRepository;
    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;
    private final PointService pointService;
    private final DeliveryTrackingClient deliveryTrackingClient;

    /**
     * {@code role}로 구매자/판매자 관점을 구분해 본인 주문 목록을 최신순으로 조회한다(MY-003/004).
     * 정산 완료 여부는 {@code order.status}가 SETTLED인지로 판단하며, 정산액은 수수료 없이
     * orderPrice 그대로다(구매 확정 시 {@link #confirmOrder}가 실제로 이 상태를 만든다).
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

    /** 배송지 등록/수정(ORDER-001) — 구매자만, 송장이 등록되기 전(PAID)에만 upsert 허용. */
    @Transactional
    public OrderShipmentResponse registerAddress(Long orderId, Long buyerId, OrderShipmentAddressRequest request) {
        Order order = findOrder(orderId, buyerId);
        if (!order.isBuyer(buyerId)) {
            throw new CustomException(ErrorCode.ORDER_BUYER_ONLY);
        }
        if (order.getStatus() != OrderStatus.PAID) {
            throw new CustomException(ErrorCode.INVALID_ORDER_STATE);
        }

        OrderShipment shipment = orderShipmentRepository.findById(orderId).orElse(null);
        if (shipment == null) {
            shipment = orderShipmentRepository.save(OrderShipment.builder()
                    .order(order)
                    .recipientName(request.recipientName())
                    .recipientPhone(request.recipientPhone())
                    .zipcode(request.zipcode())
                    .address1(request.address1())
                    .address2(request.address2())
                    .build());
        } else {
            shipment.updateAddress(
                    request.recipientName(), request.recipientPhone(), request.zipcode(),
                    request.address1(), request.address2());
        }
        return OrderShipmentResponse.from(shipment);
    }

    /** 배송지/송장 조회(ORDER-001, SHIP-002 공용) — 구매자·판매자 모두 조회 가능. */
    public OrderShipmentResponse getShipment(Long orderId, Long memberId) {
        findOrder(orderId, memberId);
        OrderShipment shipment = orderShipmentRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_SHIPMENT_NOT_FOUND));
        return OrderShipmentResponse.from(shipment);
    }

    /**
     * 송장 등록(SHIP-001) — 판매자만, PAID 상태 + 배송지 등록 완료 후에만 가능하다.
     * deliveryapi.co.kr 웹훅 구독에 성공하면 배송완료는 {@link #markShipmentDelivered}(웹훅 수신)로만
     * 반영된다. 구독에 실패하면(자격증명 없음, API 오류 등) 즉시-확정 방식으로 폴백한다.
     */
    @Transactional
    public OrderShipmentResponse registerShipment(Long orderId, Long sellerId, OrderShipmentRegisterRequest request) {
        Order order = findOrder(orderId, sellerId);
        if (!order.isSeller(sellerId)) {
            throw new CustomException(ErrorCode.ORDER_SELLER_ONLY);
        }
        if (order.getStatus() != OrderStatus.PAID || order.isRefundRequested()) {
            throw new CustomException(ErrorCode.INVALID_ORDER_STATE);
        }
        OrderShipment shipment = orderShipmentRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_SHIPMENT_ADDRESS_REQUIRED));

        LocalDateTime now = LocalDateTime.now();
        shipment.registerTracking(request.courierCode(), request.trackingNumber(), now);
        order.markShipping();

        boolean subscribed = deliveryTrackingClient.subscribe(request.courierCode(), request.trackingNumber(), orderId);
        if (!subscribed) {
            log.warn("배송 조회 웹훅 구독 실패, 즉시-확정 폴백으로 처리한다(orderId={})", orderId);
            deliver(order, shipment, now);
        }

        return OrderShipmentResponse.from(shipment);
    }

    /**
     * 배송완료 웹훅 수신(SHIP-002, deliveryapi.co.kr) — (택배사, 송장번호)로 대상 주문을 찾아 확정한다.
     * 이미 SHIPPING이 아니면(중복 웹훅 등) 조용히 무시한다(idempotent).
     */
    @Transactional
    public void markShipmentDelivered(CourierCode courier, String trackingNumber) {
        OrderShipment shipment = orderShipmentRepository.findByCourierAndTrackingNumber(courier, trackingNumber)
                .orElse(null);
        if (shipment == null) {
            log.warn("배송완료 웹훅에 매칭되는 주문이 없다(courier={}, trackingNumber={})", courier, trackingNumber);
            return;
        }
        Order order = shipment.getOrder();
        if (order.getStatus() != OrderStatus.SHIPPING) {
            return;
        }
        deliver(order, shipment, LocalDateTime.now());
    }

    private void deliver(Order order, OrderShipment shipment, LocalDateTime deliveredAt) {
        order.markDelivered(deliveredAt);
        shipment.markDelivered(deliveredAt);
    }

    /** 구매 확정 처리(ORDER-002) — 구매자만, DELIVERED 상태에서만 가능하다. */
    @Transactional
    public OrderListItemResponse confirmOrder(Long orderId, Long buyerId) {
        Order order = findOrder(orderId, buyerId);
        if (!order.isBuyer(buyerId)) {
            throw new CustomException(ErrorCode.ORDER_BUYER_ONLY);
        }
        settle(order);
        return OrderListItemResponse.from(order);
    }

    /**
     * 자동 구매 확정 배치(ORDER-003) — 배송 완료 후 3일이 지난 주문을 같은 확정 로직으로 처리한다.
     * 환불 요청이 진행 중인 주문은 조회 단계에서 제외된다.
     */
    @Transactional
    public void autoConfirmDueOrders() {
        List<Order> dueOrders = orderRepository.findByStatusAndAutoConfirmAtLessThanEqualAndRefundRequestedFalse(
                OrderStatus.DELIVERED, LocalDateTime.now());
        dueOrders.forEach(this::settle);
    }

    /** tradeEscrow → 판매자 정산 + 상태 전이(거래 완료). 수동 확정/자동 배치가 공유한다. */
    private void settle(Order order) {
        if (order.getStatus() != OrderStatus.DELIVERED || order.isRefundRequested()) {
            throw new CustomException(ErrorCode.INVALID_ORDER_STATE);
        }
        pointService.settleOrder(
                order.getBuyer().getId(), order.getSeller().getId(), order.getOrderPrice(), order.getId());
        order.confirmAndSettle();
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