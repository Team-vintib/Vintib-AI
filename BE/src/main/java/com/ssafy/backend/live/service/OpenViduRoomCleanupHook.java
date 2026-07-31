package com.ssafy.backend.live.service;

import com.ssafy.backend.global.client.OpenViduClient;
import com.ssafy.backend.live.entity.Live;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * 방송이 끝나면 OpenVidu room 을 지운다.
 *
 * <p><b>훅 안에서 곧바로 지우지 않고 커밋 후로 미룬다.</b> {@link LiveCleanupHook} 은 상태 전이
 * 트랜잭션 안에서 호출되는데, 거기서 HTTP 호출을 하면 네트워크가 끝날 때까지 DB 커넥션을 쥐고
 * 있게 된다. 미디어 서버가 죽어 있으면 <b>방송 종료 자체가 그만큼 느려지거나 실패한다</b> —
 * 정리가 안 되는 것보다 종료가 안 되는 쪽이 훨씬 나쁘다.
 *
 * <p>롤백되면 이벤트가 발행되지 않아 <b>끝나지도 않은 방송의 room 을 지우는 일도 없다.</b>
 * 이는 브로드캐스트를 커밋 후에 보내는 규칙(계획서 설계 판단 2)과 같은 이유다.
 */
@Component
@RequiredArgsConstructor
public class OpenViduRoomCleanupHook implements LiveCleanupHook {

    private final ApplicationEventPublisher eventPublisher;
    private final OpenViduClient openViduClient;

    /** 트랜잭션 안. 여기서는 발행만 한다. */
    @Override
    public void onLiveEnded(Live live) {
        if (live.getOpenviduRoom() == null) {
            return;
        }
        eventPublisher.publishEvent(new LiveRoomClosed(live.getOpenviduRoom()));
    }

    /**
     * 커밋 후. 실패는 {@link OpenViduClient} 안에서 로그로 삼킨다.
     *
     * <p>{@code fallbackExecution = true} 인 이유 — {@code @TransactionalEventListener} 는
     * <b>진행 중인 트랜잭션이 없으면 아예 실행되지 않는다.</b> 지금은 종료 경로가 항상 트랜잭션
     * 안이지만, 그렇지 않은 호출부가 나중에 생기면 정리가 조용히 사라진다.
     */
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void deleteRoomAfterCommit(LiveRoomClosed event) {
        openViduClient.deleteRoom(event.roomName());
    }

    record LiveRoomClosed(String roomName) {
    }
}
