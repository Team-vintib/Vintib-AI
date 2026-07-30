package com.ssafy.backend.global.config;

import com.ssafy.backend.global.websocket.StompAuthChannelInterceptor;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
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
 */
@Configuration
@EnableWebSocketMessageBroker
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

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
        registry.enableSimpleBroker("/topic", "/queue");
        // 클라이언트가 서버로 보내는 목적지 prefix. @MessageMapping 경로 앞에 붙는다.
        registry.setApplicationDestinationPrefixes("/app");
        registry.setUserDestinationPrefix("/user");
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(stompAuthChannelInterceptor);
    }
}