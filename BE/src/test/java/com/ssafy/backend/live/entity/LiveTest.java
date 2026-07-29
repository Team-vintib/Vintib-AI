package com.ssafy.backend.live.entity;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class LiveTest {

    private static final String TITLE = "빈티지 데님 라이브";
    private static final String THUMBNAIL_URL = "https://cdn.example.com/live/1.jpg";

    private final Member host = Member.builder()
            .email("host@example.com")
            .password("encoded")
            .name("호스트")
            .build();

    @Test
    void 예약_개설하면_SCHEDULED_상태로_방송_예정_시각만_채워진다() {
        LocalDateTime scheduledAt = LocalDateTime.of(2026, 7, 28, 20, 0);

        Live live = Live.schedule(host, TITLE, THUMBNAIL_URL, scheduledAt);

        assertThat(live.getStatus()).isEqualTo(LiveStatus.SCHEDULED);
        assertThat(live.getScheduledAt()).isEqualTo(scheduledAt);
        assertThat(live.getStartedAt()).isNull();
        assertThat(live.getEndedAt()).isNull();
    }

    @Test
    void 즉시_개설하면_LIVE_상태로_시작_시각만_채워진다() {
        LocalDateTime startedAt = LocalDateTime.of(2026, 7, 27, 21, 30);

        Live live = Live.openNow(host, TITLE, THUMBNAIL_URL, startedAt);

        assertThat(live.getStatus()).isEqualTo(LiveStatus.LIVE);
        assertThat(live.getStartedAt()).isEqualTo(startedAt);
        assertThat(live.getScheduledAt()).isNull();
        assertThat(live.getEndedAt()).isNull();
    }

    @Test
    void 개설_직후에는_호스트_제목이_유지되고_최고_시청자_수가_0이다() {
        Live live = Live.schedule(host, TITLE, THUMBNAIL_URL, LocalDateTime.of(2026, 7, 28, 20, 0));

        assertThat(live.getHost()).isSameAs(host);
        assertThat(live.getTitle()).isEqualTo(TITLE);
        assertThat(live.getThumbnailUrl()).isEqualTo(THUMBNAIL_URL);
        assertThat(live.getPeakViewerCount()).isZero();
        assertThat(live.getOpenviduRoom()).isNull();
    }
}