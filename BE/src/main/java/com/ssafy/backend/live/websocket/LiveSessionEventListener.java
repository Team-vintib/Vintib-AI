package com.ssafy.backend.live.websocket;

import com.ssafy.backend.global.websocket.StompPrincipal;
import com.ssafy.backend.live.service.LiveViewerService;
import java.security.Principal;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.messaging.SessionDisconnectEvent;
import org.springframework.web.socket.messaging.SessionSubscribeEvent;
import org.springframework.web.socket.messaging.SessionUnsubscribeEvent;

/**
 * STOMP 세션 이벤트를 시청자 수 집계로 옮긴다(-450).
 *
 * <p><b>왜 CONNECT 가 아니라 SUBSCRIBE 로 세는가.</b> CONNECT 프레임에는 어느 방송인지가 없다.
 * 연결만으로는 "라이브 목록 화면에서 붙어만 있는 사람"과 "특정 방송을 보고 있는 사람"을 구분할 수
 * 없다. 방송이 드러나는 첫 지점은 구독 목적지다.
 *
 * <p><b>집계에서 예외를 밖으로 던지지 않는다.</b> 이 리스너는 클라이언트 inbound 채널에서 돌아서,
 * Redis 장애로 예외가 새어 나가면 시청자 수뿐 아니라 <b>채팅·경매 구독까지 함께 끊긴다.</b>
 * 시청자 수는 부가 정보이므로 실패해도 실시간 기능 본체는 살아 있어야 한다.
 *
 * <p><b>호스트는 시청자에서 빠진다.</b> 그래서 구독 주체({@code StompPrincipal})를 함께 넘긴다 —
 * 판단은 {@link LiveViewerService}가 한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LiveSessionEventListener {

    /**
     * {@code /topic/lives/{liveId}} 아래의 <b>모든</b> 토픽을 한 방송의 시청으로 본다 —
     * 채팅만 구독한 사람도, 경매만 구독한 사람도 그 방송을 보고 있는 것이다. 특정 토픽
     * (예: {@code /viewers})만 세면 시청자 수 UI 를 켠 사람만 집계돼 실제보다 적게 나온다.
     */
    private static final Pattern LIVE_TOPIC = Pattern.compile("^/topic/lives/(\\d+)(?:/.*)?$");

    private final LiveViewerService liveViewerService;

    @EventListener
    public void onSubscribe(SessionSubscribeEvent event) {
        StompHeaderAccessor accessor = StompHeaderAccessor.wrap(event.getMessage());
        Long liveId = liveIdOf(accessor.getDestination());
        if (liveId == null) {
            return;
        }

        String sessionId = accessor.getSessionId();
        String subscriptionId = accessor.getSubscriptionId();
        if (sessionId == null || subscriptionId == null) {
            return;
        }

        // CONNECT 에서 심어 둔 주체다. 비회원이면 null 이며 그대로 시청자로 센다.
        Long memberId = memberIdOf(accessor.getUser());

        run("구독", sessionId, () -> liveViewerService.enter(sessionId, subscriptionId, liveId, memberId));
    }

    private Long memberIdOf(Principal principal) {
        return principal instanceof StompPrincipal stompPrincipal ? stompPrincipal.memberId() : null;
    }

    @EventListener
    public void onUnsubscribe(SessionUnsubscribeEvent event) {
        StompHeaderAccessor accessor = StompHeaderAccessor.wrap(event.getMessage());

        // UNSUBSCRIBE 프레임에는 destination 이 없다. 구독 시점에 저장한 매핑으로 방송을 되찾는다.
        String sessionId = accessor.getSessionId();
        String subscriptionId = accessor.getSubscriptionId();
        if (sessionId == null || subscriptionId == null) {
            return;
        }

        run("구독 해지", sessionId, () -> liveViewerService.leaveSubscription(sessionId, subscriptionId));
    }

    @EventListener
    public void onDisconnect(SessionDisconnectEvent event) {
        String sessionId = event.getSessionId();
        if (sessionId == null) {
            return;
        }

        run("연결 종료", sessionId, () -> liveViewerService.leaveSession(sessionId));
    }

    private Long liveIdOf(String destination) {
        if (destination == null) {
            return null;
        }
        Matcher matcher = LIVE_TOPIC.matcher(destination);
        return matcher.matches() ? Long.valueOf(matcher.group(1)) : null;
    }

    private void run(String what, String sessionId, Runnable action) {
        try {
            action.run();
        } catch (RuntimeException e) {
            log.warn("시청자 수 집계 실패({}) - sessionId={}", what, sessionId, e);
        }
    }
}
