package com.ssafy.backend.business.entity;

/**
 * 사업자 인증 상태(BIZ-001). 관리자 승인/거절 API가 아직 없어 {@code APPROVED}/{@code REJECTED}로의
 * 전이는 현재 DB를 직접 조작해야만 발생한다 — 이번 범위는 제출/조회/재제출까지다.
 *
 * <p>row 자체가 없는 "미제출" 상태는 이 enum에 없다 — 서비스 응답에서만 문자열 {@code "NONE"}으로 표현한다.
 */
public enum BusinessVerificationStatus {
    PENDING,
    APPROVED,
    REJECTED
}
