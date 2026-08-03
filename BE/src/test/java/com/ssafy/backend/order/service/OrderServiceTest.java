package com.ssafy.backend.order.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.order.dto.request.OrderCreateRequest;
import com.ssafy.backend.order.dto.request.OrderRole;
import com.ssafy.backend.order.dto.response.OrderListItemResponse;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
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

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private PointService pointService;

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
        orderService = new OrderService(orderRepository, productRepository, memberRepository, pointService);
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

        OrderListItemResponse response = orderService.createOrder(BUYER_ID, new OrderCreateRequest(PRODUCT_ID));

        assertThat(response.orderPrice()).isEqualTo(50_000L);
        assertThat(response.status()).isEqualTo("PAID");
        assertThat(realProduct.getSaleStatus().name()).isEqualTo("SOLD");
        verify(pointService).pay(eq(BUYER_ID), eq(50_000L), any());
    }

    @Test
    void 본인_상품은_구매할_수_없다() {
        when(seller.getId()).thenReturn(BUYER_ID);
        Product realProduct = realDirectSaleProduct();
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(realProduct));

        assertThatThrownBy(() -> orderService.createOrder(BUYER_ID, new OrderCreateRequest(PRODUCT_ID)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.SELF_PURCHASE_NOT_ALLOWED);
    }
}
