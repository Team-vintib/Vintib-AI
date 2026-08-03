package com.ssafy.backend.point.entity;

/** {@code point_transaction.type} — 스키마의 CHECK 제약과 그대로 맞물린다. */
public enum PointTransactionType {
    CHARGE,
    BID_HOLD,
    BID_RELEASE,
    PAYMENT,
    SETTLEMENT,
    REFUND,
    WITHDRAW
}
