package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LiveServiceTest {

    private static final Long HOST_ID = 1L;
    private static final String TITLE = "빈티지 데님 라이브";
    private static final String THUMBNAIL_URL = "https://cdn.example.com/live/1.jpg";

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private Member host;

    private LiveService liveService;

    @BeforeEach
    void setUp() {
        liveService = new LiveService(liveRepository, memberRepository, List.of());
    }

    @Test
    void 예약_개설하면_SCHEDULED_상태로_저장된다() {
        LocalDateTime scheduledAt = LocalDateTime.now().plusDays(1);
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.of(host));
        when(host.getId()).thenReturn(HOST_ID);
        when(liveRepository.save(any(Live.class))).thenAnswer(invocation -> invocation.getArgument(0));

        LiveResponse response =
                liveService.scheduleLive(HOST_ID, new LiveScheduleRequest(TITLE, THUMBNAIL_URL, scheduledAt));

        assertThat(response.status()).isEqualTo(LiveStatus.SCHEDULED);
        assertThat(response.scheduledAt()).isEqualTo(scheduledAt);
        assertThat(response.startedAt()).isNull();
        assertThat(response.hostId()).isEqualTo(HOST_ID);
        assertThat(response.title()).isEqualTo(TITLE);
    }

    @Test
    void 즉시_개설하면_LIVE_상태로_시작_시각이_박힌다() {
        LocalDateTime 개설_직전 = LocalDateTime.now();
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.of(host));
        when(host.getId()).thenReturn(HOST_ID);
        when(liveRepository.save(any(Live.class))).thenAnswer(invocation -> invocation.getArgument(0));

        LiveResponse response = liveService.openLiveNow(HOST_ID, new LiveInstantRequest(TITLE, THUMBNAIL_URL));

        assertThat(response.status()).isEqualTo(LiveStatus.LIVE);
        assertThat(response.scheduledAt()).isNull();
        // 시작 시각은 클라이언트 값이 아니라 서버 시각이어야 한다.
        assertThat(response.startedAt()).isBetween(개설_직전, LocalDateTime.now());
    }

    @Test
    void 존재하지_않는_회원이_개설하면_예외가_발생한다() {
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.empty());
        LiveScheduleRequest request =
                new LiveScheduleRequest(TITLE, THUMBNAIL_URL, LocalDateTime.now().plusDays(1));

        assertThatThrownBy(() -> liveService.scheduleLive(HOST_ID, request))
                .isInstanceOf(CustomException.class);
    }
}