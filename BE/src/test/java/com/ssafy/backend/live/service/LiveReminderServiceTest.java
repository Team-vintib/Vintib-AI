package com.ssafy.backend.live.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveReminderRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.notification.repository.NotificationRepository;
import java.time.LocalDateTime;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 예약 라이브 시작 알림(FE 요청 008 §3.2.1).
 *
 * <p>실제 DB로 돌린다 — <b>중복 방지의 근거가 unique 제약과 {@code notified_at}</b>이라 목으로는
 * 검증할 대상이 사라진다.
 */
@SpringBootTest
class LiveReminderServiceTest {

    @Autowired
    private LiveReminderService liveReminderService;

    @Autowired
    private LiveReminderRepository liveReminderRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private NotificationRepository notificationRepository;

    private Member host;
    private Member viewer;

    @BeforeEach
    void setUp() {
        host = memberRepository.save(회원("호스트"));
        viewer = memberRepository.save(회원("시청자"));
    }

    private Member 회원(String name) {
        Member member = Member.builder()
                .email("reminder-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name(name)
                .build();
        member.updateBasicInfo(
                "rm-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000000", "서울", "1층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        return member;
    }

    private Live 예약_라이브(LocalDateTime scheduledAt) {
        return liveRepository.save(Live.schedule(host, "주말 아메카지 특집", null, null, scheduledAt));
    }

    @Test
    void 예약_방송에_알림을_신청할_수_있다() {
        Live live = 예약_라이브(LocalDateTime.now().plusDays(1));

        assertThat(liveReminderService.register(viewer.getId(), live.getId()).isReminderSet()).isTrue();
        assertThat(liveReminderService.isRegistered(viewer.getId(), live.getId())).isTrue();
    }

    @Test
    void 같은_방송에_두_번_신청해도_실패하지_않는다() {
        // 중복 클릭에 에러를 띄우면 사용자는 무엇이 잘못됐는지 알 수 없다. 상태는 이미 원하는 대로다.
        Live live = 예약_라이브(LocalDateTime.now().plusDays(1));
        liveReminderService.register(viewer.getId(), live.getId());

        assertThat(liveReminderService.register(viewer.getId(), live.getId()).isReminderSet()).isTrue();
        assertThat(liveReminderRepository.findByLive_IdAndMember_Id(live.getId(), viewer.getId()))
                .isPresent();
    }

    @Test
    void 신청한_적_없어도_취소는_성공한다() {
        Live live = 예약_라이브(LocalDateTime.now().plusDays(1));

        assertThat(liveReminderService.cancel(viewer.getId(), live.getId()).isReminderSet()).isFalse();
    }

    @Test
    void 취소하면_신청_상태가_풀린다() {
        Live live = 예약_라이브(LocalDateTime.now().plusDays(1));
        liveReminderService.register(viewer.getId(), live.getId());

        liveReminderService.cancel(viewer.getId(), live.getId());

        assertThat(liveReminderService.isRegistered(viewer.getId(), live.getId())).isFalse();
    }

    @Test
    void 이미_진행_중인_방송에는_신청할_수_없다() {
        // 바로 들어가면 되는 방송에 "시작하면 알려 달라"는 뜻이 없다.
        Live live = liveRepository.save(
                Live.openNow(host, "지금 하는 방송", null, null, LocalDateTime.now()));

        Long liveId = live.getId();
        Long viewerId = viewer.getId();
        assertThatThrownBy(() -> liveReminderService.register(viewerId, liveId))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INVALID_LIVE_STATE);
    }

    @Test
    void 존재하지_않는_방송에는_신청할_수_없다() {
        Long viewerId = viewer.getId();
        assertThatThrownBy(() -> liveReminderService.register(viewerId, 999_999_999L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.LIVE_NOT_FOUND);
    }

    @Test
    void 시작이_임박하면_알림이_생성된다() {
        // 10분 전부터 대상이다. 5분 뒤 시작이면 이번 주기에 잡혀야 한다.
        Live live = 예약_라이브(LocalDateTime.now().plusMinutes(5));
        liveReminderService.register(viewer.getId(), live.getId());
        long before = notificationRepository.countByMember_IdAndReadFalse(viewer.getId());

        assertThat(liveReminderService.dispatchDue()).isPositive();

        assertThat(notificationRepository.countByMember_IdAndReadFalse(viewer.getId()))
                .isGreaterThan(before);
    }

    @Test
    void 아직_한참_남은_방송은_알림_대상이_아니다() {
        Live live = 예약_라이브(LocalDateTime.now().plusDays(1));
        liveReminderService.register(viewer.getId(), live.getId());

        liveReminderService.dispatchDue();

        assertThat(liveReminderRepository
                        .findByLive_IdAndMember_Id(live.getId(), viewer.getId())
                        .orElseThrow()
                        .getNotifiedAt())
                .isNull();
    }

    @Test
    void 같은_신청에_알림이_두_번_생성되지_않는다() {
        // 스케줄러는 1분마다 돈다. 이미 보낸 신청을 다시 집으면 알림함이 같은 문구로 도배된다.
        Live live = 예약_라이브(LocalDateTime.now().plusMinutes(5));
        liveReminderService.register(viewer.getId(), live.getId());
        liveReminderService.dispatchDue();
        long afterFirst = notificationRepository.countByMember_IdAndReadFalse(viewer.getId());

        liveReminderService.dispatchDue();

        assertThat(notificationRepository.countByMember_IdAndReadFalse(viewer.getId()))
                .isEqualTo(afterFirst);
    }
}
