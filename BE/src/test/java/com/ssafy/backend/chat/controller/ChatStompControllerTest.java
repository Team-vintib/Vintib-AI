package com.ssafy.backend.chat.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.chat.repository.ChatMessageRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.lang.reflect.Type;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.converter.JacksonJsonMessageConverter;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

/**
 * 실시간 채팅 송수신 통합 테스트(-452, -454).
 *
 * <p>실제 서버 포트를 띄우고 STOMP 클라이언트로 붙는다 — MockMvc 로는 브로드캐스트를 검증할 수 없다.
 *
 * <p><b>메시지 컨버터는 {@link JacksonJsonMessageConverter}를 직접 만들어 쓴다.</b>
 * {@code StringMessageConverter}로 보내면 SEND 프레임의 content-type 이 {@code text/plain}이 되어
 * 서버가 payload 를 DTO 로 변환하지 못한다. 이 컨버터는 내부에 자체 매퍼를 두므로 테스트 컨텍스트에
 * {@code ObjectMapper} 빈이 없어도(Spring Boot 4 모듈러 테스트) 동작한다.
 *
 * <p>응답은 {@code Map}으로 받아 필드를 직접 확인한다 — 문자열 포함 검사보다 정확하다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ChatStompControllerTest {

    private static final long TIMEOUT_SECONDS = 5;

    @LocalServerPort
    private int port;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private ChatMessageRepository chatMessageRepository;

    private WebSocketStompClient stompClient;
    private Member host;
    private String viewerToken;
    private Long liveId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        host = saveMember("호스트");
        Member viewer = saveMember("시청자");
        viewerToken = jwtTokenProvider.createAccessToken(viewer.getId(), viewer.getEmail());

        liveId = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now())).getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    private Member saveMember(String name) {
        return memberRepository.save(Member.builder()
                .email("chat-" + name + "-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name(name)
                .build());
    }

    private StompSession connect(String token) throws Exception {
        StompHeaders headers = new StompHeaders();
        if (token != null) {
            headers.add("Authorization", "Bearer " + token);
        }
        return stompClient
                .connectAsync(
                        "ws://localhost:" + port + "/ws",
                        new WebSocketHttpHeaders(),
                        headers,
                        new StompSessionHandlerAdapter() {})
                .get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
    }

    /** 지정한 목적지의 첫 프레임을 받는다. 구독 등록이 서버에 반영될 시간을 확보한 뒤 돌려준다. */
    private CompletableFuture<Map<String, Object>> subscribe(StompSession session, String destination)
            throws InterruptedException {
        CompletableFuture<Map<String, Object>> received = new CompletableFuture<>();
        session.subscribe(destination, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return Map.class;
            }

            @SuppressWarnings("unchecked")
            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                received.complete((Map<String, Object>) payload);
            }
        });
        // 구독이 반영되기 전에 발행하면 브로드캐스트를 놓친다.
        Thread.sleep(300);
        return received;
    }

    private Map<String, Object> chatPayload(String content, String clientMessageId) {
        return Map.of("content", content, "clientMessageId", clientMessageId);
    }

    @SuppressWarnings("unchecked")
    private String errorCodeOf(Map<String, Object> apiResponse) {
        return (String) ((Map<String, Object>) apiResponse.get("error")).get("code");
    }

    @Test
    void 회원이_발언하면_구독자에게_브로드캐스트되고_저장된다() throws Exception {
        StompSession sender = connect(viewerToken);
        StompSession watcher = connect(null);
        CompletableFuture<Map<String, Object>> received =
                subscribe(watcher, "/topic/lives/" + liveId + "/chat");

        long before = chatMessageRepository.count();
        sender.send("/app/lives/" + liveId + "/chat", chatPayload("사이즈 M 맞나요?", "tmp-1"));

        Map<String, Object> message = received.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(message.get("content")).isEqualTo("사이즈 M 맞나요?");
        assertThat(message.get("senderType")).isEqualTo("USER");
        assertThat(message.get("senderId")).isNotNull();
        assertThat(message.get("messageId")).isNotNull();
        // 발행자가 낙관적으로 그린 말풍선을 치환할 수 있게 임시 ID 가 그대로 돌아온다.
        assertThat(message.get("clientMessageId")).isEqualTo("tmp-1");
        assertThat(chatMessageRepository.count()).isEqualTo(before + 1);
    }

    @Test
    void 프로필_이미지는_아직_항상_null이다() throws Exception {
        // 회원 엔티티에 프로필 이미지 필드가 없다(서윤 담당). 임의로 채우면 FE 가 실제 값으로 오해한다.
        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> received =
                subscribe(sender, "/topic/lives/" + liveId + "/chat");

        sender.send("/app/lives/" + liveId + "/chat", chatPayload("프로필 확인", "tmp-p"));

        Map<String, Object> message = received.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(message.get("senderProfileImageUrl")).isNull();
    }

    @Test
    void 비회원은_구독은_되지만_발언하면_에러를_받는다() throws Exception {
        // 라이브 시청·채팅 읽기는 비회원도 가능하다. 발언만 막힌다.
        StompSession guest = connect(null);
        CompletableFuture<Map<String, Object>> errors = subscribe(guest, "/user/queue/errors");

        long before = chatMessageRepository.count();
        guest.send("/app/lives/" + liveId + "/chat", chatPayload("비회원 발언", "tmp-2"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L008");
        assertThat(chatMessageRepository.count()).isEqualTo(before);
    }

    @Test
    void 종료된_방송에는_발언할_수_없다() throws Exception {
        Live ended = liveRepository.save(Live.openNow(host, "끝난 방송", null, LocalDateTime.now()));
        ended.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        liveRepository.save(ended);

        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> errors = subscribe(sender, "/user/queue/errors");

        sender.send("/app/lives/" + ended.getId() + "/chat", chatPayload("끝난 방송에 발언", "tmp-3"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L007");
    }

    @Test
    void 공백만_있는_메시지는_거부된다() throws Exception {
        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> errors = subscribe(sender, "/user/queue/errors");

        long before = chatMessageRepository.count();
        sender.send("/app/lives/" + liveId + "/chat", chatPayload("   ", "tmp-4"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L009");
        assertThat(chatMessageRepository.count()).isEqualTo(before);
    }

    @Test
    void 길이_한도를_넘는_메시지는_거부된다() throws Exception {
        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> errors = subscribe(sender, "/user/queue/errors");

        long before = chatMessageRepository.count();
        sender.send("/app/lives/" + liveId + "/chat", chatPayload("가".repeat(501), "tmp-5"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L009");
        assertThat(chatMessageRepository.count()).isEqualTo(before);
    }
}