package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
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
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long LIVE_ID = 101L;
    private static final String TITLE = "빈티지 데님 라이브";
    private static final String THUMBNAIL_URL = "https://cdn.example.com/live/1.jpg";

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private Member host;

    @Mock
    private LiveCleanupHook cleanupHook;

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
    void 진행_중인_방송을_종료하면_ENDED로_바뀌고_정리_훅이_불린다() {
        LiveService 훅이_달린_서비스 =
                new LiveService(liveRepository, memberRepository, List.of(cleanupHook));
        when(host.getId()).thenReturn(HOST_ID);
        Live live = Live.openNow(host, TITLE, THUMBNAIL_URL, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));

        LiveResponse response = 훅이_달린_서비스.transitionStatus(
                HOST_ID, LIVE_ID, new LiveStatusUpdateRequest(LiveStatus.ENDED));

        assertThat(response.status()).isEqualTo(LiveStatus.ENDED);
        verify(cleanupHook).onLiveEnded(live);
    }

    @Test
    void 예정_방송을_시작하면_LIVE로_바뀌고_정리_훅은_불리지_않는다() {
        LiveService 훅이_달린_서비스 =
                new LiveService(liveRepository, memberRepository, List.of(cleanupHook));
        when(host.getId()).thenReturn(HOST_ID);
        Live live = Live.schedule(host, TITLE, THUMBNAIL_URL, LocalDateTime.now().plusDays(1));
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));

        LiveResponse response = 훅이_달린_서비스.transitionStatus(
                HOST_ID, LIVE_ID, new LiveStatusUpdateRequest(LiveStatus.LIVE));

        assertThat(response.status()).isEqualTo(LiveStatus.LIVE);
        assertThat(response.startedAt()).isNotNull();
        verify(cleanupHook, never()).onLiveEnded(any());
    }

    @Test
    void 허용되지_않는_전이는_거부된다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live 종료된_방송 = Live.openNow(host, TITLE, THUMBNAIL_URL, LocalDateTime.now());
        종료된_방송.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(종료된_방송));
        LiveStatusUpdateRequest request = new LiveStatusUpdateRequest(LiveStatus.LIVE);

        assertThatThrownBy(() -> liveService.transitionStatus(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_LIVE_STATE);
    }

    @Test
    void 본인_라이브가_아니면_상태를_바꿀_수_없다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live 남의_라이브 = Live.openNow(host, TITLE, THUMBNAIL_URL, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(남의_라이브));
        LiveStatusUpdateRequest request = new LiveStatusUpdateRequest(LiveStatus.ENDED);

        assertThatThrownBy(() -> liveService.transitionStatus(OTHER_MEMBER_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NOT_LIVE_HOST);
    }

    @Test
    void 존재하지_않는_라이브는_상태를_바꿀_수_없다() {
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.empty());
        LiveStatusUpdateRequest request = new LiveStatusUpdateRequest(LiveStatus.ENDED);

        assertThatThrownBy(() -> liveService.transitionStatus(HOST_ID, LIVE_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
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