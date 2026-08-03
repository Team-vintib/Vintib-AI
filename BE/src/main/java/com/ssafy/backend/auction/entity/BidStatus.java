package com.ssafy.backend.auction.entity;

/**
 * 입찰 상태. {@code bid.status} 컬럼에 문자열로 저장된다 (docs/db/erd.md §3-4).
 *
 * <p>한 경매에서 {@code ACTIVE}는 항상 최대 하나다 — 상위 입찰이 들어오면 직전 최고가는
 * {@code OUTBID}가 되고 보류된 포인트가 풀린다(AUCT-008).
 */
public enum BidStatus {

    /** 현재 최고 입찰. */
    ACTIVE,

    /** 상위 입찰에 밀림 → 포인트 보류 해제됨 (AUCT-008). */
    OUTBID,

    /** 낙찰 (AUCT-012). */
    WON,

    /** 경매 종료 시점에 최고가가 아니었음. */
    LOST
}
