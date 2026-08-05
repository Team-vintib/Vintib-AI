package com.ssafy.backend.refund.dto.request;

/** 판매자가 환불 요청을 처리할 때 고를 수 있는 결정(REFUND-002). {@code RefundStatus}와 달리 REQUESTED가 없다. */
public enum RefundDecision {
    APPROVED, // 승인
    REJECTED // 거절
}