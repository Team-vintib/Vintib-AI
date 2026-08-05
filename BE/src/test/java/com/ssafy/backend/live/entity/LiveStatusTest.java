package com.ssafy.backend.live.entity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

/**
 * 방송 상태 전이 규칙 테스트.
 *
 * <p>전이표는 {@link LiveStatus}가 소유하므로 여기서 규칙 자체를 못 박는다. 서비스 테스트는
 * "규칙을 지키는가"를, 이 테스트는 "규칙이 무엇인가"를 검증한다.
 */
class LiveStatusTest {

    @Test
    void 예정은_진행_또는_취소로만_갈_수_있다() {
        assertThat(LiveStatus.SCHEDULED.canTransitionTo(LiveStatus.LIVE)).isTrue();
        assertThat(LiveStatus.SCHEDULED.canTransitionTo(LiveStatus.CANCELED)).isTrue();
        assertThat(LiveStatus.SCHEDULED.canTransitionTo(LiveStatus.ENDED)).isFalse();
        assertThat(LiveStatus.SCHEDULED.canTransitionTo(LiveStatus.SCHEDULED)).isFalse();
    }

    @Test
    void 진행은_종료로만_갈_수_있다() {
        assertThat(LiveStatus.LIVE.canTransitionTo(LiveStatus.ENDED)).isTrue();
        assertThat(LiveStatus.LIVE.canTransitionTo(LiveStatus.SCHEDULED)).isFalse();
        assertThat(LiveStatus.LIVE.canTransitionTo(LiveStatus.CANCELED)).isFalse();
        assertThat(LiveStatus.LIVE.canTransitionTo(LiveStatus.LIVE)).isFalse();
    }

    @ParameterizedTest
    @EnumSource(LiveStatus.class)
    void 종료된_방송은_어디로도_갈_수_없다(LiveStatus target) {
        // 되돌리기를 허용하면 종료 시 정리한 리소스를 다시 살려야 한다.
        assertThat(LiveStatus.ENDED.canTransitionTo(target)).isFalse();
    }

    @ParameterizedTest
    @EnumSource(LiveStatus.class)
    void 취소된_방송은_어디로도_갈_수_없다(LiveStatus target) {
        assertThat(LiveStatus.CANCELED.canTransitionTo(target)).isFalse();
    }

    @ParameterizedTest
    @EnumSource(LiveStatus.class)
    void 목표_상태가_null이면_전이할_수_없다(LiveStatus from) {
        assertThat(from.canTransitionTo(null)).isFalse();
    }
}