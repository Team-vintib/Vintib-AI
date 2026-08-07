package com.ssafy.backend.order.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.DeliveryTrackingClient;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    private static final Long BUYER_ID = 1L;
    private static final Long SELLER_ID = 2L;
    private static final Long ORDER_ID = 10L;
    private static final Long PRODUCT_ID = 20L;
    private static final Long LIVE_ID = 101L;

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private OrderShipmentRepository orderShipmentRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveProductRepository liveProductRepository;

    @Mock
    private PointService pointService;

    @Mock
    private DeliveryTrackingClient deliveryTrackingClient;

    @Mock
    private NotificationCommandPort notificationCommandPort;

    @Mock
    private Order order;

    @Mock
    private Member buyer;

    @Mock
    private Member seller;

    @Mock
    private Product product;

    private OrderService orderService;

    @BeforeEach
    void setUp() {
        orderService = new OrderService(
                orderRepository, orderShipmentRepository, productRepository, memberRepository, liveRepository,
                liveProductRepository, pointService, deliveryTrackingClient, notificationCommandPort);
    }

    private Product realDirectSaleProduct() {
        Product real = Product.builder().seller(seller).categoryId(1L).title("빈티지 자켓").build();
        real.registerDirectSale(50_000L);
        return real;
    }

    private void stubOrderFields() {
        when(order.getId()).thenReturn(ORDER_ID);
        when(order.getProduct()).thenReturn(product);
        when(order.getBuyer()).thenReturn(buyer);
        when(order.getSeller()).thenReturn(seller);
        when(product.getSeller()).thenReturn(seller);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(order.getOrderPrice()).thenReturn(110_000L);
    }

    @Test
    void role이_BUYER면_구매_내역을_최신순으로_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        stubOrderFields();
        when(seller.getNickname()).thenReturn("판매자");
        when(order.getStatus()).thenReturn(OrderStatus.PAID);
        when(orderRepository.findByBuyer_IdOrderByCreatedAtDesc(BUYER_ID, pageable))
                .thenReturn(new PageImpl<>(List.of(order), pageable, 1));

        PageResponse<OrderListItemResponse> response = orderService.getOrders(BUYER_ID, OrderRole.BUYER, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).orderId()).isEqualTo(ORDER_ID);
        assertThat(response.content().get(0).sellerNickname()).isEqualTo("판매자");
        assertThat(response.content().get(0).status()).isEqualTo("PAID");
    }

    @Test
    void 구매_내역이_없으면_빈_목록을_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        when(orderRepository.findByBuyer_IdOrderByCreatedAtDesc(BUYER_ID, pageable))
                .thenReturn(new PageImpl<>(List.of(), pageable, 0));

        PageResponse<OrderListItemResponse> response = orderService.getOrders(BUYER_ID, OrderRole.BUYER, pageable);

        assertThat(response.content()).isEmpty();
    }

    @Test
    void role이_SELLER면_판매_정산_내역을_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        stubOrderFields();
        when(order.getStatus()).thenReturn(OrderStatus.SETTLED);
        when(orderRepository.findBySeller_IdOrderByCreatedAtDesc(SELLER_ID, pageable))
                .thenReturn(new PageImpl<>(List.of(order), pageable, 1));

        PageResponse<OrderListItemResponse> response = orderService.getOrders(SELLER_ID, OrderRole.SELLER, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).status()).isEqualTo("SETTLED");
        assertThat(response.content().get(0).orderPrice()).isEqualTo(110_000L);
    }

    @Test
    void 주문_상세_조회에_성공하면_당사자에게_반환한다() {
        stubOrderFields();
        when(order.getStatus()).thenReturn(OrderStatus.PAID);
        when(order.isPartyOf(BUYER_ID)).thenReturn(true);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));

        OrderListItemResponse response = orderService.getOrderDetail(ORDER_ID, BUYER_ID);

        assertThat(response.orderId()).isEqualTo(ORDER_ID);
    }

    @Test
    void 존재하지_않는_주문을_상세_조회하면_예외를_던진다() {
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> orderService.getOrderDetail(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ORDER_NOT_FOUND);
    }

    @Test
    void 당사자가_아니면_주문_상세_조회시_예외를_던진다() {
        Long outsiderId = 999L;
        when(order.isPartyOf(outsiderId)).thenReturn(false);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));

        assertThatThrownBy(() -> orderService.getOrderDetail(ORDER_ID, outsiderId))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVOICE_FORBIDDEN);
    }

    @Test
    void 상시_판매_상품을_구매하면_주문이_생성되고_결제된다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(buyer.getId()).thenReturn(BUYER_ID);
        Product realProduct = realDirectSaleProduct();
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(realProduct));
        when(memberRepository.findById(BUYER_ID)).thenReturn(Optional.of(buyer));
        when(orderRepository.save(any(Order.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OrderListItemResponse response = orderService.createOrder(BUYER_ID, new OrderCreateRequest(PRODUCT_ID, null));

        assertThat(response.orderPrice()).isEqualTo(50_000L);
        assertThat(response.status()).isEqualTo("PAID");
        assertThat(realProduct.getSaleStatus().name()).isEqualTo("SOLD");
        verify(pointService).pay(eq(BUYER_ID), eq(50_000L), any());
        verify(notificationCommandPort).notify(
                eq(seller), eq("ORDER_PAID"), any(), any(), eq("ORDER"), any());
    }

    @Test
    void 본인_상품은_구매할_수_없다() {
        when(seller.getId()).thenReturn(BUYER_ID);
        Product realProduct = realDirectSaleProduct();
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(realProduct));

        assertThatThrownBy(() -> orderService.createOrder(BUYER_ID, new OrderCreateRequest(PRODUCT_ID, null)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.SELF_PURCHASE_NOT_ALLOWED);
    }

    @Test
    void 배송지를_처음_등록하면_새로_생성된다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));
        when(orderShipmentRepository.findById(ORDER_ID)).thenReturn(Optional.empty());
        when(orderShipmentRepository.save(any(OrderShipment.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OrderShipmentResponse response = orderService.registerAddress(
                ORDER_ID, BUYER_ID, new OrderShipmentAddressRequest("홍길동", "010-1234-5678", "06134", "테헤란로 1", null));

        assertThat(response.recipientName()).isEqualTo("홍길동");
    }

    private OrderShipment newShipmentFor(Order realOrder) {
        return OrderShipment.builder()
                .order(realOrder).recipientName("홍길동").recipientPhone("010-1234-5678")
                .zipcode("06134").address1("테헤란로 1").build();
    }

    @Test
    void 웹훅_구독에_성공하면_송장만_등록하고_아직_배송완료로_바뀌지_않는다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));
        OrderShipment shipment = newShipmentFor(realOrder);
        when(orderShipmentRepository.findById(ORDER_ID)).thenReturn(Optional.of(shipment));
        when(deliveryTrackingClient.subscribe(CourierCode.CJ, "123456789012", ORDER_ID)).thenReturn(true);

        OrderShipmentResponse response = orderService.registerShipment(
                ORDER_ID, SELLER_ID, new OrderShipmentRegisterRequest(CourierCode.CJ, "123456789012"));

        assertThat(response.trackingNumber()).isEqualTo("123456789012");
        assertThat(response.courierCode()).isEqualTo(CourierCode.CJ);
        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.SHIPPING);
        assertThat(realOrder.getAutoConfirmAt()).isNull();
        verify(notificationCommandPort).notify(
                eq(buyer), eq("SHIPMENT_STARTED"), any(), any(), eq("ORDER"), any());
        verify(notificationCommandPort, org.mockito.Mockito.never()).notify(
                eq(buyer), eq("SHIPMENT_COMPLETED"), any(), any(), any(), any());
    }

    @Test
    void 웹훅_구독에_실패하면_즉시_배송완료로_폴백한다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));
        OrderShipment shipment = newShipmentFor(realOrder);
        when(orderShipmentRepository.findById(ORDER_ID)).thenReturn(Optional.of(shipment));
        when(deliveryTrackingClient.subscribe(CourierCode.CJ, "123456789012", ORDER_ID)).thenReturn(false);

        orderService.registerShipment(ORDER_ID, SELLER_ID, new OrderShipmentRegisterRequest(CourierCode.CJ, "123456789012"));

        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.DELIVERED);
        assertThat(realOrder.getAutoConfirmAt()).isAfter(LocalDateTime.now().plusDays(2));
        verify(notificationCommandPort).notify(
                eq(buyer), eq("SHIPMENT_STARTED"), any(), any(), eq("ORDER"), any());
        verify(notificationCommandPort).notify(
                eq(buyer), eq("SHIPMENT_COMPLETED"), any(), any(), eq("ORDER"), any());
    }

    @Test
    void 환불_요청_중인_주문은_송장을_등록할_수_없다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markRefundRequested();
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));

        assertThatThrownBy(() -> orderService.registerShipment(
                ORDER_ID, SELLER_ID, new OrderShipmentRegisterRequest(CourierCode.CJ, "123456789012")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_ORDER_STATE);
    }

    @Test
    void 배송지_미등록시_송장등록하면_예외를_던진다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));
        when(orderShipmentRepository.findById(ORDER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> orderService.registerShipment(
                ORDER_ID, SELLER_ID, new OrderShipmentRegisterRequest(CourierCode.CJ, "123456789012")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ORDER_SHIPMENT_ADDRESS_REQUIRED);
    }

    @Test
    void 배송완료_웹훅을_받으면_SHIPPING_주문이_배송완료로_바뀐다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        OrderShipment shipment = newShipmentFor(realOrder);
        when(orderShipmentRepository.findByCourierAndTrackingNumber(CourierCode.CJ, "123456789012"))
                .thenReturn(Optional.of(shipment));

        orderService.updateShipmentTracking(CourierCode.CJ, "123456789012", TrackingStatus.DELIVERED);

        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.DELIVERED);
        assertThat(shipment.getDeliveredAt()).isNotNull();
        assertThat(shipment.getTrackingStatus()).isEqualTo(TrackingStatus.DELIVERED);
        verify(notificationCommandPort).notify(
                eq(buyer), eq("SHIPMENT_COMPLETED"), any(), any(), eq("ORDER"), any());
    }

    @Test
    void 이미_배송완료된_주문에_중복_웹훅이_와도_조용히_무시한다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        realOrder.markDelivered(LocalDateTime.now());
        OrderShipment shipment = newShipmentFor(realOrder);
        when(orderShipmentRepository.findByCourierAndTrackingNumber(CourierCode.CJ, "123456789012"))
                .thenReturn(Optional.of(shipment));

        orderService.updateShipmentTracking(CourierCode.CJ, "123456789012", TrackingStatus.DELIVERED);

        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.DELIVERED);
    }

    @Test
    void 중간_배송상태_웹훅은_진행상태만_갱신하고_주문을_확정하지_않는다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        OrderShipment shipment = newShipmentFor(realOrder);
        when(orderShipmentRepository.findByCourierAndTrackingNumber(CourierCode.CJ, "123456789012"))
                .thenReturn(Optional.of(shipment));

        orderService.updateShipmentTracking(CourierCode.CJ, "123456789012", TrackingStatus.IN_TRANSIT);

        assertThat(shipment.getTrackingStatus()).isEqualTo(TrackingStatus.IN_TRANSIT);
        assertThat(shipment.getDeliveredAt()).isNull();
        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.SHIPPING);
    }

    @Test
    void 배송완료_상태에서_구매확정하면_정산되고_SETTLED로_바뀐다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        realOrder.markDelivered(LocalDateTime.now());
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));

        OrderListItemResponse response = orderService.confirmOrder(ORDER_ID, BUYER_ID);

        assertThat(response.status()).isEqualTo(OrderStatus.SETTLED.name());
        verify(pointService).settleOrder(BUYER_ID, SELLER_ID, 50_000L, realOrder.getId());
    }

    @Test
    void 환불_요청_중인_주문은_구매확정할_수_없다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        realOrder.markDelivered(LocalDateTime.now());
        realOrder.markRefundRequested();
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));

        assertThatThrownBy(() -> orderService.confirmOrder(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_ORDER_STATE);
    }

    @Test
    void 배송완료_전에는_구매확정할_수_없다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(realOrder));

        assertThatThrownBy(() -> orderService.confirmOrder(ORDER_ID, BUYER_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_ORDER_STATE);
    }

    @Test
    void 배송완료_경과일이_지난_주문은_자동으로_구매확정된다() {
        Order realOrder = Order.createDirectSale(buyer, seller, realDirectSaleProduct(), null, 50_000L);
        realOrder.markShipping();
        realOrder.markDelivered(LocalDateTime.now().minusDays(8));
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(orderRepository.findByStatusAndAutoConfirmAtLessThanEqualAndRefundRequestedFalse(
                eq(OrderStatus.DELIVERED), any()))
                .thenReturn(List.of(realOrder));

        orderService.autoConfirmDueOrders();

        assertThat(realOrder.getStatus()).isEqualTo(OrderStatus.SETTLED);
        verify(pointService).settleOrder(BUYER_ID, SELLER_ID, 50_000L, realOrder.getId());
    }

    // ---------- 정찰 판매 실시간 전파 (JY013) ----------

    @Test
    void 진행_중_방송에_편성된_상품이_팔리면_전파_이벤트가_만들어진다() {
        when(liveProductRepository.findRunningLiveIdsByProductId(PRODUCT_ID)).thenReturn(List.of(LIVE_ID));

        var event = orderService.resolveDirectSaleSoldEvent(PRODUCT_ID);

        assertThat(event).isPresent();
        assertThat(event.get().liveId()).isEqualTo(LIVE_ID);
        assertThat(event.get().productId()).isEqualTo(PRODUCT_ID);
        // FE 가 분기 없이 그대로 대입할 수 있게 두 값은 고정이다.
        assertThat(event.get().saleStatus()).isEqualTo("SOLD");
        assertThat(event.get().soldVia()).isEqualTo("DIRECT_SALE");
    }

    @Test
    void 진행_중_방송에_편성되지_않은_상품은_전파하지_않는다() {
        // 라이브와 무관한 일반 상시 판매 구매 — 쏠 방송이 없다.
        when(liveProductRepository.findRunningLiveIdsByProductId(PRODUCT_ID)).thenReturn(List.of());

        assertThat(orderService.resolveDirectSaleSoldEvent(PRODUCT_ID)).isEmpty();
    }

    @Test
    void 진행_중_방송이_둘_이상이면_전파하지_않는다() {
        // 어느 쪽을 골라도 나머지 방송의 큐가 어긋난다. 잘못 고르느니 쏘지 않는다.
        when(liveProductRepository.findRunningLiveIdsByProductId(PRODUCT_ID))
                .thenReturn(List.of(LIVE_ID, LIVE_ID + 1));

        assertThat(orderService.resolveDirectSaleSoldEvent(PRODUCT_ID)).isEmpty();
    }
}