package com.ssafy.backend.global.websocket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.UUID;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.converter.StringMessageConverter;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

/**
 * STOMP 핸드셰이크·CONNECT 인증 검증(-447).
 *
 * <p>실제 서버 포트를 띄운다 — MockMvc 로는 WebSocket 업그레이드를 검증할 수 없다.
 *
 * <p><b>이 테스트가 고정하는 핵심 규칙은 "토큰이 없으면 익명으로 통과, 잘못된 토큰만 거부"다.</b>
 * 비회원도 라이브를 보고 채팅을 읽을 수 있어야 하므로 연결 자체를 막으면 안 되고, 반대로 만료된
 * 토큰을 조용히 비회원으로 강등시키면 FE 가 발언이 막히는 이유를 알 수 없다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class StompConnectionTest {

    @LocalServerPort
    private int port;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    private WebSocketStompClient stompClient;
    private String memberToken;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new StringMessageConverter());

        String email = "ws-member-" + UUID.randomUUID() + "@example.com";
        Member member = memberRepository.save(Member.builder()
                .email(email)
                .password("encoded")
                .name("시청자")
                .build());
        memberToken = jwtTokenProvider.createAccessToken(member.getId(), email);
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    private String wsUrl() {
        return "ws://localhost:" + port + "/ws";
    }

    private StompSession connect(StompHeaders connectHeaders) throws Exception {
        return stompClient
                .connectAsync(wsUrl(), new org.springframework.web.socket.WebSocketHttpHeaders(),
                        connectHeaders, new org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter() {})
                .get(5, TimeUnit.SECONDS);
    }

    @Test
    void 유효한_토큰으로_CONNECT하면_연결된다() throws Exception {
        StompHeaders headers = new StompHeaders();
        headers.add("Authorization", "Bearer " + memberToken);

        StompSession session = connect(headers);

        assertThat(session.isConnected()).isTrue();
        session.disconnect();
    }

    @Test
    void 토큰이_없어도_비회원으로_연결된다() throws Exception {
        // 라이브 시청·채팅 읽기는 비회원도 가능하다. 핸드셰이크를 막으면 화면 자체가 안 뜬다.
        StompSession session = connect(new StompHeaders());

        assertThat(session.isConnected()).isTrue();
        session.disconnect();
    }

    @Test
    void 잘못된_토큰으로_CONNECT하면_거부된다() throws Exception {
        // 조용히 비회원으로 강등시키지 않는다 — 만료된 토큰인지 비회원인지 FE 가 구분해야 한다.
        //
        // 같은 테스트에서 익명 연결이 성공하는 것을 먼저 확인한다. 이게 없으면 엔드포인트 경로가
        // 깨져 아무도 못 붙는 상황에서도 이 테스트가 초록불로 통과한다 — 거부 원인이
        // "토큰이 잘못됨"임을 이 대조가 보장한다.
        StompSession anonymous = connect(new StompHeaders());
        assertThat(anonymous.isConnected()).isTrue();
        anonymous.disconnect();

        StompHeaders headers = new StompHeaders();
        headers.add("Authorization", "Bearer this.is.not.a.valid.jwt");

        assertThatThrownBy(() -> connect(headers)).isInstanceOf(ExecutionException.class);
    }

    @Test
    void Bearer_접두사가_없으면_토큰을_무시하고_비회원으로_연결된다() throws Exception {
        // Authorization 헤더 형식이 어긋난 것은 "토큰 없음"과 같이 취급한다.
        StompHeaders headers = new StompHeaders();
        headers.add("Authorization", memberToken);

        StompSession session = connect(headers);

        assertThat(session.isConnected()).isTrue();
        session.disconnect();
    }
}