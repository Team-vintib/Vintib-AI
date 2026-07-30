package com.ssafy.backend.global.websocket;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.stereotype.Component;

/**
 * STOMP CONNECT 프레임의 JWT를 검증해 세션에 {@link StompPrincipal}을 심는다.
 *
 * <p><b>왜 HTTP 핸드셰이크가 아니라 CONNECT 프레임인가.</b> 브라우저 {@code WebSocket} API는
 * 핸드셰이크 요청에 {@code Authorization} 헤더를 붙일 수 없다. 그래서 토큰을 STOMP CONNECT
 * 프레임의 native header로 받는다. FE는 STOMP 클라이언트의 connect headers에 실어 보낸다.
 *
 * <p><b>토큰이 없으면 익명으로 통과시킨다.</b> 라이브 시청·채팅 읽기는 비회원도 가능해야 하므로
 * 연결 자체를 막으면 안 된다. 반대로 토큰이 <b>있는데 유효하지 않으면</b> 거부한다 — 만료된
 * 토큰으로 붙은 사용자를 조용히 비회원으로 강등시키면, 발언이 막히는 이유를 FE가 알 수 없다.
 *
 * <p>{@link JwtTokenProvider}를 HTTP 필터와 공유하므로 토큰 규칙이 두 갈래로 갈라지지 않는다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class StompAuthChannelInterceptor implements ChannelInterceptor {

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor =
                MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);

        // CONNECT 에서만 인증한다. 이후 프레임은 세션에 심어둔 principal 을 그대로 쓴다.
        if (accessor == null || accessor.getCommand() != StompCommand.CONNECT) {
            return message;
        }

        String token = resolveToken(accessor);
        if (token == null) {
            return message;
        }

        // 유효하지 않으면 CustomException 이 그대로 올라가 CONNECT 가 ERROR 프레임으로 끊긴다.
        jwtTokenProvider.validateToken(token);
        accessor.setUser(new StompPrincipal(jwtTokenProvider.getMemberId(token)));

        return message;
    }

    private String resolveToken(StompHeaderAccessor accessor) {
        String header = accessor.getFirstNativeHeader(AUTHORIZATION_HEADER);
        if (header == null || !header.startsWith(BEARER_PREFIX)) {
            return null;
        }
        return header.substring(BEARER_PREFIX.length());
    }
}