package com.ssafy.backend.refund.entity;

/** 환불 요청 사유(REFUND-001). 기능정의서에 나열된 사유만 허용한다 — 단순 변심은 없다. */
public enum RefundReason {
    NOT_AS_DESCRIBED, // 상품 설명 불일치
    UNDISCLOSED_DEFECT, // 미고지 하자
    NOT_SHIPPED, // 미발송
    DUPLICATE_PAYMENT, // 중복 결제
    SYSTEM_ERROR // 시스템 오류
}