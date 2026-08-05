package com.ssafy.backend.global.config;

import com.ssafy.backend.global.websocket.StompAuthChannelInterceptor;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * 실시간 계층의 토대(INFRA). 채팅·시청자 수·반응·경매 이벤트가 모두 이 위에 올라간다.
 *
 * <p><b>브로커는 Spring 내장 SimpleBroker를 쓴다.</b> 백엔드 인스턴스가 1대라 Redis Pub/Sub이나
 * 외부 브로커(RabbitMQ 등)의 이득이 없다. 확장이 필요해지면 {@link #configureMessageBroker}
 * 한 곳만 {@code enableStompBrokerRelay}로 바꾼다.
 *
 * <p><b>SockJS는 쓰지 않는다.</b> FE가 Vue 3 + 최신 브라우저 대상이라 fallback이 필요 없고,
 * 끼우면 URL·프레임 규약이 바뀌어 테스트까지 복잡해진다.
 *
 * <h2>하트비트를 켜는 이유 (FE 요청 028)</h2>
 *
 * <p>시청자 수 집계는 WebSocket close({@code SessionDisconnectEvent})에만 기대어 세션을 뺀다.
 * 그런데 <b>모바일 망 전환·절전·탭 크래시·프록시 유휴 끊김처럼 close 가 서버에 도달하지 않는
 * 경로가 있다.</b> 그러면 죽은 sessionId 가 Redis 집합에 남아 시청자 수가 부풀고, 남은 양이
 * 세션마다 달라 "같은 방송인데 화면마다 수가 다른" 증상이 된다.
 *
 * <p>하트비트를 켜면 정해진 간격 안에 클라이언트 프레임이 오지 않을 때 브로커가 세션을 끊고,
 * 그 끊김이 다시 {@code SessionDisconnectEvent} 로 이어져 집계가 정리된다 — 반쯤 열린 커넥션을
 * 서버가 스스로 감지할 <b>유일한</b> 수단이다.
 */
@Configuration
@EnableWebSocketMessageBroker
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    /**
     * 하트비트 간격(ms). 서버가 보내는 주기이자 클라이언트에게 기대하는 주기다.
     *
     * <p>실제 값은 CONNECT 시 클라이언트와 협상된다. FE 는 {@code heart-beat: 10000,0} 으로
     * 붙으므로 — 보낼 수는 있고 받기는 원하지 않는다는 뜻 — <b>서버→클라이언트 하트비트는 아예
     * 나가지 않고, 클라이언트→서버만 10초 주기로 성립한다.</b> 우리가 필요한 것이 그쪽(죽은
     * 세션 감지)이라 이 조합으로 충분하다.
     */
    private static final long HEARTBEAT_INTERVAL_MS = 10_000;

    private final StompAuthChannelInterceptor stompAuthChannelInterceptor;

    /**
     * STOMP 핸드셰이크 허용 오리진. HTTP CORS({@code SecurityConfig.corsConfigurationSource})와
     * <b>별개로 지정해야 한다</b> — WebSocket 핸드셰이크는 Spring MVC의 CORS 처리를 타지 않는다.
     * 값은 같은 설정 키를 공유해 두 곳이 어긋나지 않게 한다.
     */
    @Value("${cors.allowed-origins}")
    private List<String> allowedOrigins;

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns(allowedOrigins.toArray(String[]::new));
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // 구독 목적지. /queue 는 특정 세션에게만 보내는 에러 통보(/user/queue/errors)용이다.
        registry.enableSimpleBroker("/topic", "/queue")
                // 하트비트를 쓰려면 스케줄러가 반드시 있어야 한다 — 없이 값만 주면 기동이 실패한다.
                .setTaskScheduler(webSocketHeartbeatScheduler())
                .setHeartbeatValue(new long[] {HEARTBEAT_INTERVAL_MS, HEARTBEAT_INTERVAL_MS});
        // 클라이언트가 서버로 보내는 목적지 prefix. @MessageMapping 경로 앞에 붙는다.
        registry.setApplicationDestinationPrefixes("/app");
        registry.setUserDestinationPrefix("/user");
    }

    /**
     * 브로커 하트비트 전용 스케줄러.
     *
     * <p><b>{@code @Scheduled} 용 스케줄러를 같이 쓰지 않는다.</b> 부트가 자동 구성하는
     * {@code taskScheduler} 는 기본 풀 크기가 1인데, 우리는 경매 마감 스캐너를 1초마다 돌린다
     * (@link com.ssafy.backend.auction.service.AuctionCloseScheduler}). 그 작업이 한 번이라도
     * 늦어지면 하트비트가 함께 밀려 멀쩡한 세션이 끊긴다.
     */
    @Bean
    public TaskScheduler webSocketHeartbeatScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(1);
        scheduler.setThreadNamePrefix("ws-heartbeat-");
        scheduler.initialize();
        return scheduler;
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(stompAuthChannelInterceptor);
    }
}