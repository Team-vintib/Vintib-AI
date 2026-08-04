package com.ssafy.backend.global.client;

import java.time.OffsetDateTime;

/** 토스페이먼츠 결제 승인 응답(POST /v1/payments/confirm) 중 필요한 필드만 담는다. */
public record TossPaymentConfirmResponse(
        String paymentKey, String orderId, String status, Long totalAmount, OffsetDateTime approvedAt) {
}
