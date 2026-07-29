package com.ssafy.backend.live.entity;

import java.util.Set;

/**
 * 방송 상태. {@code live.status} 컬럼에 문자열로 저장된다 (docs/db/erd.md §3-2).
 *
 * <p>상품 판매 상태({@code SaleStatus})와는 별개의 축이다 — 기능정의서 HOME-001이
 * 둘을 구분해 표시하도록 정하고 있다. enum 이름은 홈 응답(HOME-001)의
 * {@code broadcastStatus} 문자열과 그대로 일치시켜, 매핑 시 별도 변환표가 필요 없게 한다.
 *
 * <p><b>전이 규칙을 enum이 소유한다.</b> 서비스마다 if 문으로 흩어 놓으면 한 곳을 고칠 때
 * 다른 곳이 남는다. 허용 전이는 아래 {@code allowedTransitions} 한 곳에만 적는다.
 */
public enum LiveStatus {

    /** 예정 — 예약 개설(LIVE-001) 직후 상태. {@code scheduledAt}이 채워져 있다. */
    SCHEDULED,

    /** 진행 중 — 즉시 개설(LIVE-002)이면 생성 시점부터 이 상태다. */
    LIVE,

    /** 종료. */
    ENDED,

    /** 방송 전 취소. */
    CANCELED;

    /**
     * 이 상태에서 넘어갈 수 있는 상태들.
     *
     * <p>{@code ENDED}·{@code CANCELED}는 종착점이라 어디로도 가지 않는다. 되돌리기를 허용하면
     * 종료 시 정리한 리소스(경매·채팅방)를 다시 살려야 하는데, 그 복구 경로를 만들 이유가 없다.
     */
    private Set<LiveStatus> allowedTransitions() {
        return switch (this) {
            case SCHEDULED -> Set.of(LIVE, CANCELED);
            case LIVE -> Set.of(ENDED);
            case ENDED, CANCELED -> Set.of();
        };
    }

    public boolean canTransitionTo(LiveStatus target) {
        return target != null && allowedTransitions().contains(target);
    }
}