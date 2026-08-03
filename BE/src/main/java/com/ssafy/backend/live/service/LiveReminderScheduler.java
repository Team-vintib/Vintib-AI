package com.ssafy.backend.live.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 예약 라이브 알림 발송 주기 실행(FE 요청 008 §3.2.1).
 *
 * <p><b>스케줄러는 "언제 돌지"만 안다.</b> 무엇을 보낼지는 {@link LiveReminderService}가
 * 정한다 — 트랜잭션 경계도 거기 있어야 발송 표시와 알림 생성이 함께 커밋된다.
 *
 * <p>{@code fixedDelay}를 쓴다. {@code fixedRate}는 한 번이 늦어지면 다음 실행이 겹쳐 들어와
 * 같은 신청을 두 번 집을 수 있다(발송 표시가 아직 커밋 전이다). {@code fixedDelay}는 이전
 * 실행이 끝난 뒤부터 세므로 그 겹침이 없다.
 *
 * <p><b>서버가 여러 대가 되면 이 방식으로는 부족하다</b> — 인스턴스마다 스케줄러가 돌아
 * 같은 신청을 동시에 집는다. 지금은 EC2 한 대라 문제가 없고, 늘어나면 락(ShedLock 등)이
 * 필요하다. 그때까지의 최소 안전장치로 {@code notified_at}과 unique 제약을 둔다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LiveReminderScheduler {

    private static final long INTERVAL_MS = 60_000;

    private final LiveReminderService liveReminderService;

    @Scheduled(fixedDelay = INTERVAL_MS, initialDelay = INTERVAL_MS)
    public void dispatch() {
        try {
            liveReminderService.dispatchDue();
        } catch (Exception e) {
            // 여기서 예외가 새어 나가면 스케줄러가 통째로 멈춘다. 다음 주기에 다시 시도한다.
            log.error("예약 라이브 알림 발송 실패 - 다음 주기에 재시도한다", e);
        }
    }
}
