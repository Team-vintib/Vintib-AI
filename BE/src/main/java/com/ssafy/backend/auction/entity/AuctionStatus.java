package com.ssafy.backend.auction.entity;

/**
 * 경매 상태. {@code auction.status} 컬럼에 문자열로 저장된다 (docs/db/erd.md §3-3).
 *
 * <p>상품 판매 상태({@code SaleStatus})와 짝을 이루지만 별개다 — 경매가 {@code RUNNING}인
 * 동안 상품은 {@code AUCTION_IN_PROGRESS}가 된다.
 */
public enum AuctionStatus {

    /** 조건 설정 완료, 시작 전 (AUCT-001). */
    READY,

    /** 진행 중 (AUCT-002). 한 라이브에서 이 상태는 동시에 하나뿐이다 (LIVE-004). */
    RUNNING,

    /** 낙찰 (AUCT-012). 낙찰자·낙찰가가 반드시 채워져 있다. */
    SUCCESS,

    /** 입찰자 없이 종료 — 미낙찰 (AUCT-014). */
    FAILED,

    /** 취소. */
    CANCELED
}