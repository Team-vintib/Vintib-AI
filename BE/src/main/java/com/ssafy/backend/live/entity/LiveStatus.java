package com.ssafy.backend.live.entity;

/**
 * 방송 상태. {@code live.status} 컬럼에 문자열로 저장된다 (docs/db/erd.md §3-2).
 *
 * <p>상품 판매 상태({@code SaleStatus})와는 별개의 축이다 — 기능정의서 HOME-001이
 * 둘을 구분해 표시하도록 정하고 있다. enum 이름은 홈 응답(HOME-001)의
 * {@code broadcastStatus} 문자열과 그대로 일치시켜, 매핑 시 별도 변환표가 필요 없게 한다.
 */
public enum LiveStatus {

    /** 예정 — 예약 개설(LIVE-001) 직후 상태. {@code scheduledAt}이 채워져 있다. */
    SCHEDULED,

    /** 진행 중 — 즉시 개설(LIVE-002)이면 생성 시점부터 이 상태다. */
    LIVE,

    /** 종료. */
    ENDED,

    /** 방송 전 취소. */
    CANCELED
}