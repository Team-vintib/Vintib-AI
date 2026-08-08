package com.ssafy.backend.refund.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.notification.port.NotificationCommandPort;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.refund.dto.request.RefundCreateRequest;
import com.ssafy.backend.refund.dto.request.RefundDecision;
import com.ssafy.backend.refund.dto.request.RefundReviewRequest;
import com.ssafy.backend.refund.dto.response.RefundResponse;
import com.ssafy.backend.refund.entity.RefundReason;
import com.ssafy.backend.refund.entity.RefundRequest;
import com.ssafy.backend.refund.entity.RefundStatus;
import com.ssafy.backend.refund.repository.RefundRequestRepository;
import java.time.LocalDateTime;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RefundServiceTest {

    private static final Long BUYER_ID = 1L;
    private static final Long SELLER_ID = 2L;
    private static final Long ORDER_ID = 10L;
    private static final Long REFUND_ID = 100L;

    @Mock
    private RefundRequestRepository refundRequestRepository;

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PointService pointService;

    @Mock
    private NotificationCommandPort notificationCommandPort;

    @Mock
    private Member buyer;

    @Mock
    private Member seller;

    @Mock
    private Product product;

    private RefundService refundService;

    @BeforeEach
    void setUp() {
        refundService =
                new RefundService(refundRequestRepository, orderRepository, pointService, notificationCommandPort);
    }

    private Order orderWith(OrderStatus status) {
        Order order = Order.createDirectSale(buyer, seller, product, null, 50_000L);
        if (status == OrderStatus.SHIPPING || status == OrderStatus.DELIVERED) {
            order.markShipping();
        }
        if (status == OrderStatus.DELIVERED) {
            order.markDelivered(java.time.LocalDateTime.now());
        }
        return order;
    }

    @Test
    void 배송중_주문에_환불을_요청하면_주문에_표시되고_저장된다() {
        Order order = orderWith(OrderStatus.SHIPPING);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(refundRequestRepository.findFirstByOrder_IdAndStatus(ORDER_ID, RefundStatus.REQUESTED))
                .thenReturn(Optional.empty());
        when(refundRequestRepository.save(any(RefundRequest.class))).thenAnswer(invocation -> invocation.getArgument(0));

        RefundResponse response = refundService.requestRefund(
                ORDER_ID, BUYER_ID, new RefundCreateRequest(RefundReason.NOT_SHIPPED, "아직도 발송되지 않았습니다."));

        assertThat(order.isRefundRequested()).isTrue();
        assertThat(response.status()).isEqualTo(RefundStatus.REQUESTED.name());
        assertThat(response.reason()).isEqualTo(RefundReason.NOT_SHIPPED.name());
        verify(notificationCommandPort).notify(
                eq(seller), eq("REFUND_REQUESTED"), any(), any(), eq("ORDER"), eq(order.getId()));
    }

    @Test
    void 정산완료된_주문은_환불을_요청할_수_없다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        order.confirmAndSettle(LocalDateTime.now());
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));

        assertThatThrownBy(() -> refundService.requestRefund(
                ORDER_ID, BUYER_ID, new RefundCreateRequest(RefundReason.UNDISCLOSED_DEFECT, "하자 발견")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_ORDER_STATE);
    }

    @Test
    void 이미_진행중인_환불_요청이_있으면_거부한다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));
        when(refundRequestRepository.findFirstByOrder_IdAndStatus(ORDER_ID, RefundStatus.REQUESTED))
                .thenReturn(Optional.of(RefundRequest.builder().order(order).reason(RefundReason.UNDISCLOSED_DEFECT)
                        .detailReason("이전 요청").build()));

        assertThatThrownBy(() -> refundService.requestRefund(
                ORDER_ID, BUYER_ID, new RefundCreateRequest(RefundReason.UNDISCLOSED_DEFECT, "새 요청")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.REFUND_ALREADY_REQUESTED);
    }

    @Test
    void 구매자가_아니면_환불_요청을_거부한다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(orderRepository.findById(ORDER_ID)).thenReturn(Optional.of(order));

        assertThatThrownBy(() -> refundService.requestRefund(
                ORDER_ID, SELLER_ID, new RefundCreateRequest(RefundReason.UNDISCLOSED_DEFECT, "하자 발견")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ORDER_BUYER_ONLY);
    }

    @Test
    void 판매자가_승인하면_포인트가_환급되고_주문이_REFUNDED로_바뀐다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        order.markRefundRequested();
        RefundRequest refund = RefundRequest.builder().order(order)
                .reason(RefundReason.UNDISCLOSED_DEFECT).detailReason("하자 발견").build();
        when(buyer.getId()).thenReturn(BUYER_ID);
        when(seller.getId()).thenReturn(SELLER_ID);
        when(refundRequestRepository.findById(REFUND_ID)).thenReturn(Optional.of(refund));

        RefundResponse response = refundService.reviewRefund(
                REFUND_ID, SELLER_ID, new RefundReviewRequest(RefundDecision.APPROVED, null));

        assertThat(order.getStatus()).isEqualTo(OrderStatus.REFUNDED);
        assertThat(order.isRefundRequested()).isFalse();
        assertThat(response.status()).isEqualTo(RefundStatus.APPROVED.name());
        verify(pointService).refundOrder(BUYER_ID, 50_000L, order.getId());
        // 승인 결과 알림은 pointService.refundOrder()(POINT_REFUNDED)가 이미 보낸다 — RefundService가
        // 직접 또 만들면 같은 이벤트에 알림이 두 번 생긴다.
        verify(notificationCommandPort, never()).notify(any(), any(), any(), any(), any(), any());
    }

    @Test
    void 판매자가_거절하면_주문_상태는_그대로_유지된다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        order.markRefundRequested();
        RefundRequest refund = RefundRequest.builder().order(order)
                .reason(RefundReason.UNDISCLOSED_DEFECT).detailReason("하자 발견").build();
        when(seller.getId()).thenReturn(SELLER_ID);
        when(refundRequestRepository.findById(REFUND_ID)).thenReturn(Optional.of(refund));

        RefundResponse response = refundService.reviewRefund(
                REFUND_ID, SELLER_ID, new RefundReviewRequest(RefundDecision.REJECTED, "하자를 확인할 수 없습니다."));

        assertThat(order.getStatus()).isEqualTo(OrderStatus.DELIVERED);
        assertThat(order.isRefundRequested()).isFalse();
        assertThat(response.status()).isEqualTo(RefundStatus.REJECTED.name());
        assertThat(response.rejectionReason()).isEqualTo("하자를 확인할 수 없습니다.");
        verify(pointService, never()).refundOrder(any(), any(), any());
        verify(notificationCommandPort).notify(
                eq(buyer), eq("REFUND_REJECTED"), any(), eq("하자를 확인할 수 없습니다."), eq("ORDER"), eq(order.getId()));
    }

    @Test
    void 거절_사유가_없으면_예외를_던진다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        order.markRefundRequested();
        RefundRequest refund = RefundRequest.builder().order(order)
                .reason(RefundReason.UNDISCLOSED_DEFECT).detailReason("하자 발견").build();
        when(seller.getId()).thenReturn(SELLER_ID);
        when(refundRequestRepository.findById(REFUND_ID)).thenReturn(Optional.of(refund));

        assertThatThrownBy(() -> refundService.reviewRefund(
                REFUND_ID, SELLER_ID, new RefundReviewRequest(RefundDecision.REJECTED, " ")))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_INPUT_VALUE);
    }

    @Test
    void 판매자가_아니면_승인을_거부한다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        order.markRefundRequested();
        RefundRequest refund = RefundRequest.builder().order(order)
                .reason(RefundReason.UNDISCLOSED_DEFECT).detailReason("하자 발견").build();
        when(seller.getId()).thenReturn(SELLER_ID);
        when(refundRequestRepository.findById(REFUND_ID)).thenReturn(Optional.of(refund));

        assertThatThrownBy(() -> refundService.reviewRefund(
                REFUND_ID, BUYER_ID, new RefundReviewRequest(RefundDecision.APPROVED, null)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ORDER_SELLER_ONLY);
    }

    @Test
    void 이미_처리된_요청을_다시_처리하면_예외를_던진다() {
        Order order = orderWith(OrderStatus.DELIVERED);
        RefundRequest refund = RefundRequest.builder().order(order)
                .reason(RefundReason.UNDISCLOSED_DEFECT).detailReason("하자 발견").build();
        refund.approve(java.time.LocalDateTime.now());
        when(seller.getId()).thenReturn(SELLER_ID);
        when(refundRequestRepository.findById(REFUND_ID)).thenReturn(Optional.of(refund));

        assertThatThrownBy(() -> refundService.reviewRefund(
                REFUND_ID, SELLER_ID, new RefundReviewRequest(RefundDecision.APPROVED, null)))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.REFUND_ALREADY_REVIEWED);
    }
}