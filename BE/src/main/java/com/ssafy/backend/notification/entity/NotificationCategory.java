package com.ssafy.backend.notification.entity;

import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 알림 목록 조회/일괄 읽음 처리를 걸러 낼 카테고리. DB 컬럼이 아니라 {@link Notification#getType()}
 * 값에서 계산해서 나가는 필터/응답 전용 값.
 *
 * <p>{@code TRADE}는 나머지 카테고리에 안 걸리는 모든 type의 catch-all이다(고정 목록 없음). 새 type을
 * 추가했는데 이 enum에 매핑을 깜빡해도 조회 자체가 깨지지 않고 자동으로 TRADE로 떨어진다 — 다만 의도한
 * 카테고리로 분류하려면 매핑을 잊지 말아야 한다.
 */
public enum NotificationCategory {

    LIVE(Set.of("LIVE_REMINDER", "LIVE_STARTED")),
    AUCTION(Set.of("AUCTION_OUTBID", "AUCTION_WON")),
    SHIPPING(Set.of("SHIPMENT_STARTED", "SHIPMENT_COMPLETED")),
    POINT(Set.of("POINT_CHARGED", "POINT_REFUNDED", "WITHDRAW_COMPLETED")),
    TRADE(Set.of());

    private final Set<String> types;

    NotificationCategory(Set<String> types) {
        this.types = types;
    }

    // enum 상수는 다른 static 필드보다 먼저 초기화되므로 여기서 values()를 안전하게 순회할 수 있다.
    private static final Set<String> CATEGORIZED_TYPES = Arrays.stream(values())
            .filter(category -> category != TRADE)
            .flatMap(category -> category.types.stream())
            .collect(Collectors.toUnmodifiableSet());

    public boolean isCatchAll() {
        return this == TRADE;
    }

    /** IN 조건에 쓸 고정 type 목록. {@code TRADE}는 고정 목록이 없다 — 먼저 {@link #isCatchAll()}로 분기할 것. */
    public Set<String> types() {
        if (isCatchAll()) {
            throw new IllegalStateException("TRADE는 catch-all이라 고정 type 목록이 없다 — excludedTypesForCatchAll()을 쓸 것");
        }
        return types;
    }

    /** {@code TRADE}(catch-all) 조회에 쓸 NOT IN 대상 — 나머지 카테고리에 속하는 type 전체. */
    public static Set<String> excludedTypesForCatchAll() {
        return CATEGORIZED_TYPES;
    }
}