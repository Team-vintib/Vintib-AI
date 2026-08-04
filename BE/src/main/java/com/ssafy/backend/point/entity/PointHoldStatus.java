package com.ssafy.backend.point.entity;

/**
 * 입찰 보류 상태. {@code point_hold.status} 컬럼에 문자열로 저장된다(docs/db/erd.md §4).
 *
 * <p>한 회원은 <b>전체 경매를 통틀어</b> {@code HELD}가 동시에 하나뿐이다 — 최고 입찰자인 동안
 * 다른 경매에 입찰할 수 없고(AUCT-009), 같은 이유로 자기 자신을 연속 상위 입찰할 수도 없다
 * (AUCT-006, 이미 {@code HELD}를 쥐고 있어 두 번째 보류를 만들 수 없다). DB 부분 UNIQUE 인덱스
 * {@code ux_point_hold_member_active}가 이 규칙의 최후 방어선이다.
 */
public enum PointHoldStatus {

    /** 보류 중 — 이 회원이 해당 경매의 최고 입찰자다. */
    HELD,

    /** 상위 입찰 발생으로 해제됨 (AUCT-008). */
    RELEASED,

    /** 낙찰되어 거래 대금으로 전환됨 (AUCT-012, 다음 단계). */
    CONVERTED
}
