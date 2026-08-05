package com.ssafy.backend.order.dto.request;

/** 마이페이지 주문 목록 조회(MY-003/004) 시 조회 관점을 구분하는 쿼리 파라미터. */
public enum OrderRole {
    BUYER,
    SELLER
}