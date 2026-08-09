package com.ssafy.backend.order.service;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.live.dto.response.LiveProductSoldResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.notification.port.NotificationCommandPort;
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
import com.ssafy.backend.order.entity.TrackingStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.order.repository.OrderShipmentRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 주문 조회, 정찰제 주문 생성, 배송지·송장,
 * 구매 확정·정산({@link #confirmOrder}/{@link #autoConfirmDueOrders}).
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
    private final LiveRepository liveRepository;
    private final LiveProductRepository liveProductRepository;
    private final PointService pointService;
    private final DeliveryTrackingClient deliveryTrackingClient;
    private final NotificationCommandPort notificationCommandPort;

    /**
     * {@code role}로 구매자/판매자 관점을 구분해 본인 주문 목록을 최신순으로 조회한다.
     * 정산 완료 여부는 {@code order.status}가 SETTLED인지로 판단하며, 정산액은 수수료 없이
     * orderPrice 그대로다(구매 확정 시 {@link #confirmOrder}가 실제로 이 상태를 만든다).
     */
    public PageResponse<OrderListItemResponse> getOrders(Long memberId, OrderRole role, Pageable pageable) {
        Page<Order> orders = role == OrderRole.BUYER
                ? orderRepository.findByBuyer_IdOrderByCreatedAtDesc(memberId, pageable)
                : orderRepository.findBySeller_IdOrderByCreatedAtDesc(memberId, pageable);
        return PageResponse.from(orders.map(OrderListItemResponse::from));
    }

    /** 주문 상세 조회. 경로에 userId가 없어 order.isPartyOf(principal)로 권한을 확인한다. */
    public OrderListItemResponse getOrderDetail(Long orderId, Long memberId) {
        return OrderListItemResponse.from(findOrder(orderId, memberId));
    }

    /**
     * 정찰제 즉시구매. 결제(포인트 보관), 주문 생성, 상품 SOLD 처리를 한 트랜잭션으로 묶는다.
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
        // 라이브 시청 화면에서 산 주문만 방송이 붙는다 — 방송 종료 요약이 이 값으로
        // 판매 실적을 집계한다. 없는 방송 ID를 보내면 404로 막는다(무시하면 요약에서 빠진 이유를 FE가 알 수 없기 때문).
        Live live = request.liveId() == null ? null : liveRepository.findById(request.liveId())
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
        Order order = orderRepository.save(
                Order.createDirectSale(buyer, product.getSeller(), product, live, product.getPrice()));

        pointService.pay(buyerId, product.getPrice(), order.getId());
        product.markSold();

        notificationCommandPort.notify(
                order.getSeller(),
                "ORDER_PAID",
                "상품이 판매되었습니다",
                "주문이 결제됐어요. 배송지를 확인하고 송장을 등록해주세요.",
                "ORDER",
                order.getId());

        return OrderListItemResponse.from(order);
    }

    /**
     * 방금 팔린 상품을 시청자에게 알릴 이벤트(JY013). 그 상품이 <b>진행 중 방송에 편성돼
     * 있을 때만</b> 값이 있다.
     *
     * <p><b>왜 {@code createOrder} 안에서 쏘지 않는가.</b> 그 메서드는 {@code @Transactional}
     * 이라 거기서 발행하면 커밋 전에 나간다. 이후 롤백되면 시청자 화면에서만 상품이 사라진 채
     * 남는다. 그래서 "쏠 내용"만 여기서 만들고 발행은 컨트롤러가 커밋 이후에 한다 —
     * {@code LiveController.changeCurrentProduct} · {@code AuctionCloseScheduler} 와 같은 규칙이다.
     *
     * <p><b>주문의 {@code liveId} 를 쓰지 않는다.</b> 상품 상세 화면에서 사면 그 값이 없지만,
     * 그래도 진행 중 방송에 걸려 있으면 큐에서 빠져야 하기 때문이다. 주문의 {@code liveId} 는
     * "어느 방송의 실적으로 집계할지"를 정하는 별개의 값이다.
     */
    public Optional<LiveProductSoldResponse> resolveDirectSaleSoldEvent(Long productId) {
        List<Long> runningLiveIds = liveProductRepository.findRunningLiveIdsByProductId(productId);
        if (runningLiveIds.isEmpty()) {
            return Optional.empty();
        }
        if (runningLiveIds.size() > 1) {
            // 한 상품이 진행 중 방송 두 곳에 걸린 상태다. 어느 쪽을 고르든 나머지 방송의 큐가
            // 어긋나므로 아무 데도 쏘지 않고 로그만 남긴다 — 잘못 고르는 것보다 낫다.
            log.warn("진행 중 방송이 둘 이상이라 판매 전파를 건너뛴다(productId={}, liveIds={})",
                    productId, runningLiveIds);
            return Optional.empty();
        }
        return Optional.of(LiveProductSoldResponse.directSale(
                runningLiveIds.get(0), productId, LocalDateTime.now()));
    }

    /** 배송지 등록/수정 — 구매자만, 송장이 등록되기 전(PAID)에만 upsert 허용. */
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

    /** 배송지/송장 조회 — 구매자·판매자 모두 조회 가능. */
    public OrderShipmentResponse getShipment(Long orderId, Long memberId) {
        findOrder(orderId, memberId);
        OrderShipment shipment = orderShipmentRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_SHIPMENT_NOT_FOUND));
        return OrderShipmentResponse.from(shipment);
    }

    /**
     * 송장 등록 — 판매자만, PAID 상태 + 배송지 등록 완료 후에만 가능하다.
     * deliveryapi.co.kr 웹훅 구독에 성공하면 배송완료는 {@link #updateShipmentTracking}(웹훅 수신)로만
     * 반영된다. 구독에 실패하면(자격증명 없음, API 오류 등) 즉시-확정 방식으로 폴백.
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

        notificationCommandPort.notify(
                order.getBuyer(),
                "SHIPMENT_STARTED",
                "배송이 시작되었습니다",
                "판매자가 송장을 등록했어요.",
                "ORDER",
                order.getId());

        boolean subscribed = deliveryTrackingClient.subscribe(request.courierCode(), request.trackingNumber(), orderId);
        if (!subscribed) {
            log.warn("배송 조회 웹훅 구독 실패, 즉시-확정 폴백으로 처리한다(orderId={})", orderId);
            deliver(order, shipment, now);
        }

        return OrderShipmentResponse.from(shipment);
    }

    /**
     * 배송 진행 상태 웹훅 수신(deliveryapi.co.kr) — (택배사, 송장번호)로 대상 주문을 찾아
     * 진행 상태를 갱신. {@code DELIVERED}면 기존 확정 로직까지. 이미 SHIPPING이
     * 아니면(중복 웹훅 등) 확정만 조용히 무시(idempotent) — 상태 갱신 자체는 계속 반영.
     */
    @Transactional
    public void updateShipmentTracking(CourierCode courier, String trackingNumber, TrackingStatus status) {
        OrderShipment shipment = orderShipmentRepository.findByCourierAndTrackingNumber(courier, trackingNumber)
                .orElse(null);
        if (shipment == null) {
            log.warn("배송 웹훅에 매칭되는 주문이 없다(courier={}, trackingNumber={})", courier, trackingNumber);
            return;
        }
        shipment.updateTrackingStatus(status);

        Order order = shipment.getOrder();
        if (status == TrackingStatus.DELIVERED && order.getStatus() == OrderStatus.SHIPPING) {
            deliver(order, shipment, LocalDateTime.now());
        }
    }

    private void deliver(Order order, OrderShipment shipment, LocalDateTime deliveredAt) {
        order.markDelivered(deliveredAt);
        shipment.markDelivered(deliveredAt);
        // 즉시-확정 폴백 경로(구독 실패)는 웹훅이 없어 trackingStatus를 아무도 안 채운다 —
        // 여기서 맞춰준다. 웹훅 경로는 updateShipmentTracking()이 이미 DELIVERED로 채워둔
        // 뒤라 멱등하게 덮어쓸 뿐이다(045).
        shipment.updateTrackingStatus(TrackingStatus.DELIVERED);
        notificationCommandPort.notify(
                order.getBuyer(),
                "SHIPMENT_COMPLETED",
                "배송이 완료되었습니다",
                "구매를 확정하면 거래가 끝나요. 확정하지 않으면 3일 후 자동으로 처리됩니다.",
                "ORDER",
                order.getId());
    }

    /** 구매 확정 처리 — 구매자만, DELIVERED 상태에서만 가능. */
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
     * 자동 구매 확정 배치 — 배송 완료 후 3일이 지난 주문을 같은 확정 로직으로 처리.
     * 환불 요청이 진행 중인 주문은 조회 단계에서 제외.
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
        order.confirmAndSettle(LocalDateTime.now());
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