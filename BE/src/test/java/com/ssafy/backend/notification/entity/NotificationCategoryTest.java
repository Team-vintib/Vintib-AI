package com.ssafy.backend.notification.entity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class NotificationCategoryTest {

    @Test
    void 카테고리별로_매핑된_type_목록을_반환한다() {
        assertThat(NotificationCategory.LIVE.types()).containsExactlyInAnyOrder("LIVE_REMINDER", "LIVE_STARTED");
        assertThat(NotificationCategory.AUCTION.types()).containsExactlyInAnyOrder("AUCTION_OUTBID", "AUCTION_WON");
        assertThat(NotificationCategory.SHIPPING.types())
                .containsExactlyInAnyOrder("SHIPMENT_STARTED", "SHIPMENT_COMPLETED");
        assertThat(NotificationCategory.POINT.types())
                .containsExactlyInAnyOrder("POINT_CHARGED", "POINT_REFUNDED", "WITHDRAW_COMPLETED");
    }

    @Test
    void TRADE는_catch_all이라_고정_type_목록을_요청하면_예외를_던진다() {
        assertThat(NotificationCategory.TRADE.isCatchAll()).isTrue();
        assertThatThrownBy(() -> NotificationCategory.TRADE.types()).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void TRADE의_제외_대상은_나머지_카테고리_type_전체다() {
        assertThat(NotificationCategory.excludedTypesForCatchAll())
                .containsExactlyInAnyOrder(
                        "LIVE_REMINDER", "LIVE_STARTED",
                        "AUCTION_OUTBID", "AUCTION_WON",
                        "SHIPMENT_STARTED", "SHIPMENT_COMPLETED",
                        "POINT_CHARGED", "POINT_REFUNDED", "WITHDRAW_COMPLETED");
    }

    @Test
    void 라이브_경매_배송_포인트가_아닌_type은_TRADE로_떨어진다() {
        // ORDER_PAID는 어느 카테고리에도 매핑되지 않는다 — 제외 목록에 없으므로 NOT IN 조회에서 TRADE로 남는다.
        assertThat(NotificationCategory.excludedTypesForCatchAll()).doesNotContain("ORDER_PAID");
    }
}
