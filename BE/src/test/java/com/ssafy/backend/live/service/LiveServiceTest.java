package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveListSort;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
import com.ssafy.backend.live.dto.response.LiveDetailResponse;
import com.ssafy.backend.live.dto.response.LiveListItemResponse;
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
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class LiveServiceTest {

    private static final Long HOST_ID = 1L;
    private static final Long OTHER_MEMBER_ID = 2L;
    private static final Long LIVE_ID = 101L;
    private static final List<Long> PRODUCT_IDS = List.of(2001L);
    private static final String TITLE = "빈티지 데님 라이브";
    private static final String THUMBNAIL_URL = "https://cdn.example.com/live/1.jpg";

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private Member host;

    @Mock
    private LiveProductService liveProductService;

    @Mock
    private LiveCleanupHook cleanupHook;

    @Mock
    private LiveViewerService liveViewerService;

    private LiveService liveService;

    @BeforeEach
    void setUp() {
        liveService = new LiveService(
                liveRepository, memberRepository, liveProductService, liveViewerService, List.of());
    }

    @Test
    void 예약_개설하면_SCHEDULED_상태로_저장된다() {
        LocalDateTime scheduledAt = LocalDateTime.now().plusDays(1);
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.of(host));
        when(host.getId()).thenReturn(HOST_ID);
        when(liveRepository.save(any(Live.class))).thenAnswer(invocation -> invocation.getArgument(0));

        LiveResponse response =
                liveService.scheduleLive(HOST_ID, new LiveScheduleRequest(TITLE, THUMBNAIL_URL, scheduledAt, PRODUCT_IDS));

        assertThat(response.status()).isEqualTo(LiveStatus.SCHEDULED);
        assertThat(response.scheduledAt()).isEqualTo(scheduledAt);
        assertThat(response.startedAt()).isNull();
        assertThat(response.hostId()).isEqualTo(HOST_ID);
        assertThat(response.title()).isEqualTo(TITLE);
        // 상품 편성은 개설과 같은 트랜잭션에서 함께 이뤄진다 — 빈 방이 만들어지면 안 된다.
        verify(liveProductService).linkProductsOnCreate(eq(HOST_ID), any(Live.class), eq(PRODUCT_IDS));
    }

    @Test
    void 즉시_개설하면_LIVE_상태로_시작_시각이_박힌다() {
        LocalDateTime 개설_직전 = LocalDateTime.now();
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.of(host));
        when(host.getId()).thenReturn(HOST_ID);
        when(liveRepository.save(any(Live.class))).thenAnswer(invocation -> invocation.getArgument(0));

        LiveResponse response = liveService.openLiveNow(HOST_ID, new LiveInstantRequest(TITLE, THUMBNAIL_URL, PRODUCT_IDS));

        assertThat(response.status()).isEqualTo(LiveStatus.LIVE);
        assertThat(response.scheduledAt()).isNull();
        // 시작 시각은 클라이언트 값이 아니라 서버 시각이어야 한다.
        assertThat(response.startedAt()).isBetween(개설_직전, LocalDateTime.now());
        // 즉시 개설은 곧바로 진행 중이 되어 이후 편성을 못 바꾸므로, 개설 시 반드시 편성돼야 한다.
        verify(liveProductService).linkProductsOnCreate(eq(HOST_ID), any(Live.class), eq(PRODUCT_IDS));
    }

    @Test
    void 진행_중인_방송을_종료하면_ENDED로_바뀌고_정리_훅이_불린다() {
        LiveService 훅이_달린_서비스 =
                new LiveService(
                        liveRepository, memberRepository, liveProductService, liveViewerService, List.of(cleanupHook));
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
                new LiveService(
                        liveRepository, memberRepository, liveProductService, liveViewerService, List.of(cleanupHook));
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
    void 시청_조회는_방_정보와_편성_상품을_함께_반환한다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live live = Live.openNow(host, TITLE, THUMBNAIL_URL, LocalDateTime.now());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(liveProductService.getLinkedProducts(LIVE_ID)).thenReturn(List.of());
        when(liveViewerService.getViewerCount(LIVE_ID)).thenReturn(37);

        LiveDetailResponse response = liveService.getLiveDetail(LIVE_ID);

        assertThat(response.status()).isEqualTo(LiveStatus.LIVE);
        assertThat(response.title()).isEqualTo(TITLE);
        assertThat(response.hostId()).isEqualTo(HOST_ID);
        assertThat(response.products()).isEmpty();
        // 최고치는 아직 갱신된 적이 없고, 현재 값은 실시간 집계에서 온다 — 두 필드는 별개다.
        assertThat(response.peakViewerCount()).isZero();
        assertThat(response.currentViewerCount()).isEqualTo(37);
    }

    @Test
    void 존재하지_않는_라이브는_시청_조회할_수_없다() {
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> liveService.getLiveDetail(LIVE_ID))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
    }

    @Test
    void 존재하지_않는_회원이_개설하면_예외가_발생한다() {
        when(memberRepository.findById(HOST_ID)).thenReturn(Optional.empty());
        LiveScheduleRequest request =
                new LiveScheduleRequest(TITLE, THUMBNAIL_URL, LocalDateTime.now().plusDays(1), PRODUCT_IDS);

        assertThatThrownBy(() -> liveService.scheduleLive(HOST_ID, request))
                .isInstanceOf(CustomException.class);
    }

    @Test
    void 호스트_필터에_전체_상태를_넘기면_종료_취소된_방송도_포함해_반환한다() {
        when(host.getId()).thenReturn(HOST_ID);
        Live ended = Live.schedule(host, TITLE, THUMBNAIL_URL, LocalDateTime.now().plusDays(1));
        ReflectionTestUtils.setField(ended, "id", LIVE_ID);
        ReflectionTestUtils.setField(ended, "status", LiveStatus.ENDED);
        Page<Live> page = new PageImpl<>(List.of(ended), PageRequest.of(0, 20), 1);
        when(liveRepository.findPublicLives(
                eq(LiveService.ALL_STATUSES), eq(false), any(), eq(true), eq(HOST_ID), any(Pageable.class)))
                .thenReturn(page);

        PageResponse<LiveListItemResponse> response =
                liveService.getLives(null, HOST_ID, LiveService.ALL_STATUSES, LiveListSort.LATEST, 0, 20);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).broadcastStatus()).isEqualTo(LiveStatus.ENDED);
    }
}