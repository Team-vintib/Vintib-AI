package com.ssafy.backend.live.service;

import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.dto.response.LiveStatusResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 예약 라이브 자동 시작 주기 실행(JY010).
 *
 * <p><b>{@link LiveReminderScheduler}와 같은 이유로 {@code fixedDelay}를 쓴다</b> — 한 번이
 * 늦어져도 다음 실행이 겹쳐 들어오지 않는다.
 *
 * <p><b>여기서 직접 브로드캐스트하는 이유.</b> {@code /topic/lives/{liveId}/status} 전송은
 * 원래 {@code LiveController}가 커밋 이후에 맡는다. 스케줄러는 컨트롤러를 거치지 않으므로,
 * 전이에 성공한 라이브마다 이 컴포넌트가 같은 payload를 직접 쏜다 — 이게 없으면 시청 중인
 * 화면이 "방송 시작 전"에 멈춰 있다가 새로고침해야 LIVE로 넘어간다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LiveAutoStartScheduler {

    private static final long INTERVAL_MS = 30_000;

    private final LiveService liveService;
    private final SimpMessagingTemplate messagingTemplate;

    @Scheduled(fixedDelay = INTERVAL_MS, initialDelay = INTERVAL_MS)
    public void autoStart() {
        try {
            for (LiveResponse started : liveService.autoStartDueLives()) {
                messagingTemplate.convertAndSend(
                        "/topic/lives/" + started.id() + "/status", LiveStatusResponse.from(started));
            }
        } catch (Exception e) {
            // 여기서 예외가 새어 나가면 스케줄러가 통째로 멈춘다. 다음 주기에 다시 시도한다.
            log.error("예약 라이브 자동 시작 실패 - 다음 주기에 재시도한다", e);
        }
    }
}
