package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.response.LiveReminderResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveReminder;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.notification.port.NotificationCommandPort;
import com.ssafy.backend.live.repository.LiveReminderRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 예약 라이브 시작 알림(FE 요청 008 §3.2.1).
 *
 * <p>신청·취소는 사용자가 누를 때, 발송은 {@link LiveReminderScheduler}가 주기적으로 한다.
 *
 * <h2>정책</h2>
 * <ul>
 *   <li><b>예정(SCHEDULED) 방송에만 신청할 수 있다.</b> 이미 진행 중이면 신청할 이유가 없고
 *       (바로 들어가면 된다), 종료·취소된 방송은 시작할 일이 없다.</li>
 *   <li><b>호스트 본인도 신청할 수 있다.</b> 막을 이유가 없고, 막으면 FE가 화면마다 예외를
 *       처리해야 한다.</li>
 *   <li><b>중복 신청은 성공으로 본다.</b> 같은 버튼을 두 번 눌렀을 때 에러를 띄우면 사용자는
 *       무엇이 잘못됐는지 알 수 없다 — 상태가 이미 원하는 대로이므로 그대로 돌려준다.</li>
 * </ul>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LiveReminderService {

    /** 시작 몇 분 전에 알릴지. 방송 준비 시간을 감안한 값이라 정책이 바뀌면 여기만 고친다. */
    static final int NOTIFY_BEFORE_MINUTES = 10;

    /** 한 번에 처리할 신청 수. 알림이 몰려도 한 트랜잭션이 지나치게 길어지지 않게 끊는다. */
    private static final int BATCH_SIZE = 200;

    private static final List<LiveStatus> NOTIFIABLE_STATUSES =
            List.of(LiveStatus.SCHEDULED, LiveStatus.LIVE);

    private final LiveReminderRepository liveReminderRepository;
    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;
    private final NotificationCommandPort notificationCommandPort;

    @Transactional
    public LiveReminderResponse register(Long memberId, Long liveId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));
        if (live.getStatus() != LiveStatus.SCHEDULED) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }
        // 이미 신청돼 있으면 아무것도 하지 않고 성공으로 돌려준다.
        //
        // ⚠️ 제약 위반을 잡아서 처리하지 않는 이유. 같은 트랜잭션 안에서 DataIntegrityViolationException
        //    을 catch 해도 트랜잭션은 이미 rollback-only 로 찍혀 있어 커밋 시점에 터진다. 잡아서
        //    삼키는 코드가 오히려 "성공했는데 롤백되는" 상태를 만든다.
        //    따라서 조회로 거르고, 정말 동시에 눌린 극소수 경합은 unique 제약이 막게 둔다.
        if (liveReminderRepository.existsByLive_IdAndMember_Id(liveId, memberId)) {
            return LiveReminderResponse.of(liveId, true);
        }

        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        liveReminderRepository.save(LiveReminder.of(live, member, LocalDateTime.now()));

        return LiveReminderResponse.of(liveId, true);
    }

    /** 취소는 신청이 없어도 성공이다 — 결과 상태(신청 안 됨)가 이미 원하는 대로다. */
    @Transactional
    public LiveReminderResponse cancel(Long memberId, Long liveId) {
        liveReminderRepository.findByLive_IdAndMember_Id(liveId, memberId)
                .ifPresent(liveReminderRepository::delete);
        return LiveReminderResponse.of(liveId, false);
    }

    @Transactional(readOnly = true)
    public boolean isRegistered(Long memberId, Long liveId) {
        return memberId != null && liveReminderRepository.existsByLive_IdAndMember_Id(liveId, memberId);
    }

    /**
     * 보낼 때가 된 알림을 만든다.
     *
     * <p><b>발송 표시와 알림 생성이 한 트랜잭션이다.</b> 따로 커밋하면 중간에 죽었을 때
     * 알림만 나가고 표시가 안 남아 다음 주기에 또 보낸다.
     *
     * @return 만든 알림 수
     */
    @Transactional
    public int dispatchDue() {
        LocalDateTime now = LocalDateTime.now();
        List<LiveReminder> due = liveReminderRepository.findDue(
                NOTIFIABLE_STATUSES,
                now.plusMinutes(NOTIFY_BEFORE_MINUTES),
                PageRequest.of(0, BATCH_SIZE));

        due.forEach(reminder -> {
            Live live = reminder.getLive();
            notificationCommandPort.notify(
                    reminder.getMember(),
                    "LIVE_REMINDER",
                    "곧 시작하는 방송이 있어요",
                    "'%s' 방송이 곧 시작합니다.".formatted(live.getTitle()),
                    "LIVE",
                    live.getId());
            reminder.markNotified(now);
        });

        if (!due.isEmpty()) {
            log.info("예약 라이브 알림 발송 - {}건", due.size());
        }
        return due.size();
    }
}
