package com.ssafy.backend.live.service;

import com.ssafy.backend.live.entity.Live;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 기본 정리 훅. 아직 정리할 리소스가 없어 종료 사실만 남긴다.
 *
 * <p>구현체가 하나도 없으면 훅 호출 경로가 실제로 도는지 확인할 방법이 없어, 로그만 남기는
 * 구현을 하나 둔다. 경매 마감·채팅방 닫기·OpenVidu room 해제는 각각 별도 구현체로 추가한다.
 */
@Slf4j
@Component
public class LoggingLiveCleanupHook implements LiveCleanupHook {

    @Override
    public void onLiveEnded(Live live) {
        log.info("라이브 종료 - liveId={}, hostId={}", live.getId(), live.getHost().getId());
    }
}