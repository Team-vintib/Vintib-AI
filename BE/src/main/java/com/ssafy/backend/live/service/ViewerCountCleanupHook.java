package com.ssafy.backend.live.service;

import com.ssafy.backend.live.entity.Live;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * 방송 종료 시 시청자 집합을 지운다.
 *
 * <p>종료되면 시청자는 곧 연결을 끊지만 <b>DISCONNECT 가 언제 올지는 클라이언트에 달려 있다.</b>
 * 탭을 켜 둔 채 방치하면 세션이 살아 있어 종료된 방송에 시청자 수가 계속 남는다. 종료 시점에
 * 서버가 먼저 지워 "끝난 방송에 시청자 30명"을 없앤다.
 *
 * <p>{@code peak_viewer_count} 는 건드리지 않는다 — 그건 방송이 끝난 뒤에 보는 기록이다.
 */
@Component
@RequiredArgsConstructor
public class ViewerCountCleanupHook implements LiveCleanupHook {

    private final LiveViewerService liveViewerService;

    @Override
    public void onLiveEnded(Live live) {
        liveViewerService.clear(live.getId());
    }
}
