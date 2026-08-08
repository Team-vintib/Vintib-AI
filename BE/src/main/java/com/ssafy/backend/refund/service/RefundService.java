package com.ssafy.backend.refund.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.notification.port.NotificationCommandPort;
import com.ssafy.backend.order.entity.Order;
import com.ssafy.backend.order.entity.OrderStatus;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.service.PointService;
import com.ssafy.backend.refund.dto.request.RefundCreateRequest;
import com.ssafy.backend.refund.dto.request.RefundDecision;
import com.ssafy.backend.refund.dto.request.RefundReviewRequest;
import com.ssafy.backend.refund.dto.response.RefundResponse;
import com.ssafy.backend.refund.entity.RefundRequest;
import com.ssafy.backend.refund.entity.RefundStatus;
import com.ssafy.backend.refund.repository.RefundRequestRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 환불 요청(REFUND-001)·승인/거절(REFUND-002). 승인 주체는 판매자.
 *
 * <p>환불 요청은 {@code PAID}/{@code SHIPPING}/{@code DELIVERED} 상태에서만 가능하다 — 구매 확정
 * (수동/자동)으로 이미 판매자에게 정산된 주문은 환불 불가하다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class RefundService {

    private final RefundRequestRepository refundRequestRepository;
    private final OrderRepository orderRepository;
    private final PointService pointService;
    private final NotificationCommandPort notificationCommandPort;

    /** 환불 요청(REFUND-001) — 구매자만, 환불 가능한 상태이고 진행 중인 요청이 없어야 한다. */
    @Transactional
    public RefundResponse requestRefund(Long orderId, Long buyerId, RefundCreateRequest request) {
        Order order = findOrder(orderId);
        if (!order.isBuyer(buyerId)) {
            throw new CustomException(ErrorCode.ORDER_BUYER_ONLY);
        }
        if (!isRefundable(order.getStatus()) || order.isRefundRequested()) {
            throw new CustomException(ErrorCode.INVALID_ORDER_STATE);
        }
        refundRequestRepository.findFirstByOrder_IdAndStatus(orderId, RefundStatus.REQUESTED)
                .ifPresent(existing -> {
                    throw new CustomException(ErrorCode.REFUND_ALREADY_REQUESTED);
                });

        order.markRefundRequested();
        RefundRequest refund = refundRequestRepository.save(RefundRequest.builder()
                .order(order)
                .reason(request.reason())
                .detailReason(request.detailReason())
                .build());
        notificationCommandPort.notify(
                order.getSeller(),
                "REFUND_REQUESTED",
                "환불 요청이 접수되었습니다",
                "구매자가 환불을 요청했어요. 주문을 확인해주세요.",
                "ORDER",
                order.getId());
        return RefundResponse.from(refund);
    }

    /** 환불 요청 목록 조회(REFUND-001) — 구매자·판매자 모두 조회 가능, 최신순. */
    public List<RefundResponse> getRefunds(Long orderId, Long memberId) {
        Order order = findOrder(orderId);
        if (!order.isPartyOf(memberId)) {
            throw new CustomException(ErrorCode.INVOICE_FORBIDDEN);
        }
        return refundRequestRepository.findByOrder_IdOrderByCreatedAtDesc(orderId).stream()
                .map(RefundResponse::from)
                .toList();
    }

    /**
     * 환불 승인/거절 처리(REFUND-002) — 판매자만, 아직 REQUESTED 상태인 요청만 처리할 수 있다.
     * 승인 시 {@link PointService#refundOrder}로 구매자 available에 바로 환급하고 주문을 REFUNDED로
     * 전이한다. 거절 시 주문 상태는 요청 이전 그대로 이어간다.
     */
    @Transactional
    public RefundResponse reviewRefund(Long refundId, Long sellerId, RefundReviewRequest request) {
        RefundRequest refund = refundRequestRepository.findById(refundId)
                .orElseThrow(() -> new CustomException(ErrorCode.REFUND_NOT_FOUND));
        Order order = refund.getOrder();
        if (!order.isSeller(sellerId)) {
            throw new CustomException(ErrorCode.ORDER_SELLER_ONLY);
        }
        if (!refund.isRequested()) {
            throw new CustomException(ErrorCode.REFUND_ALREADY_REVIEWED);
        }

        LocalDateTime now = LocalDateTime.now();
        if (request.decision() == RefundDecision.APPROVED) {
            // 승인 결과 알림은 여기서 따로 만들지 않는다 — pointService.refundOrder()가 이미
            // 구매자에게 POINT_REFUNDED("환불이 완료되었습니다")를 보낸다(041 §3.1-1 승인 케이스는
            // 이걸로 충족). 같은 이벤트에 알림을 두 번 만들지 않기 위함이다.
            pointService.refundOrder(order.getBuyer().getId(), order.getOrderPrice(), order.getId());
            order.markRefunded();
            refund.approve(now);
        } else {
            if (request.rejectionReason() == null || request.rejectionReason().isBlank()) {
                throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
            }
            order.clearRefundRequested();
            refund.reject(request.rejectionReason(), now);
            notificationCommandPort.notify(
                    order.getBuyer(),
                    "REFUND_REJECTED",
                    "환불 요청이 거절되었습니다",
                    request.rejectionReason(),
                    "ORDER",
                    order.getId());
        }
        return RefundResponse.from(refund);
    }

    private boolean isRefundable(OrderStatus status) {
        return status == OrderStatus.PAID || status == OrderStatus.SHIPPING || status == OrderStatus.DELIVERED;
    }

    private Order findOrder(Long orderId) {
        return orderRepository.findById(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.ORDER_NOT_FOUND));
    }
}