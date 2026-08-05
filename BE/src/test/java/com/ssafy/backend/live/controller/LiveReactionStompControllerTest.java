package com.ssafy.backend.live.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.lang.reflect.Type;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.messaging.converter.JacksonJsonMessageConverter;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

/**
 * 반응 이모지 송수신 통합 테스트.
 *
 * <p>채팅 테스트와 같은 이유로 실제 포트를 띄우고 {@link JacksonJsonMessageConverter}를 쓴다 —
 * {@code StringMessageConverter}는 SEND 프레임 content-type 을 {@code text/plain}으로 만들어
 * 서버가 payload 를 DTO 로 변환하지 못한다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LiveReactionStompControllerTest {

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
    private StringRedisTemplate redisTemplate;

    private WebSocketStompClient stompClient;
    private Member host;
    private Member viewer;
    private String viewerToken;
    private Long liveId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        host = saveMember("호스트");
        viewer = saveMember("시청자");
        viewerToken = jwtTokenProvider.createAccessToken(viewer.getId(), viewer.getEmail());

        liveId = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now())).getId();

        // rate limit 은 방송·회원 단위 키라 새 회원·새 방송이면 이미 비어 있다. 남은 창이
        // 겹치지 않도록 명시적으로도 지운다.
        redisTemplate.delete("live:reaction:" + liveId + ":" + viewer.getId());
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    private Member saveMember(String name) {
        return memberRepository.save(Member.builder()
                .email("reaction-" + name + "-" + UUID.randomUUID() + "@example.com")
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

    private CompletableFuture<Map<String, Object>> subscribeOnce(StompSession session, String destination)
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

    /** 여러 프레임을 순서대로 모은다 — rate limit 처럼 "몇 건이 통과했는지"를 봐야 하는 경우. */
    private List<Map<String, Object>> subscribeAll(StompSession session, String destination)
            throws InterruptedException {
        List<Map<String, Object>> frames = new CopyOnWriteArrayList<>();
        session.subscribe(destination, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return Map.class;
            }

            @SuppressWarnings("unchecked")
            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                frames.add((Map<String, Object>) payload);
            }
        });
        Thread.sleep(300);
        return frames;
    }

    @SuppressWarnings("unchecked")
    private String errorCodeOf(Map<String, Object> apiResponse) {
        return (String) ((Map<String, Object>) apiResponse.get("error")).get("code");
    }

    @Test
    void 회원이_반응을_보내면_구독자에게_브로드캐스트된다() throws Exception {
        StompSession sender = connect(viewerToken);
        StompSession watcher = connect(null);
        CompletableFuture<Map<String, Object>> received =
                subscribeOnce(watcher, "/topic/lives/" + liveId + "/reactions");

        sender.send("/app/lives/" + liveId + "/reactions", Map.of("type", "HEART"));

        Map<String, Object> reaction = received.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(reaction.get("type")).isEqualTo("HEART");
        assertThat(reaction.get("liveId")).isEqualTo(liveId.intValue());
        // 발행자가 낙관적으로 그린 자기 반응을 걸러낼 수 있어야 한다.
        assertThat(reaction.get("senderId")).isEqualTo(viewer.getId().intValue());
        assertThat(reaction.get("sentAt")).isNotNull();
    }

    @Test
    void 비회원은_구독은_되지만_반응을_보내면_에러를_받는다() throws Exception {
        StompSession guest = connect(null);
        CompletableFuture<Map<String, Object>> errors = subscribeOnce(guest, "/user/queue/errors");

        guest.send("/app/lives/" + liveId + "/reactions", Map.of("type", "FIRE"));

        // 채팅(L008)과 다른 코드로 온다 — FE 가 각각 다르게 안내할 수 있어야 한다.
        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L010");
    }

    @Test
    void 종료된_방송에는_반응할_수_없다() throws Exception {
        Live ended = liveRepository.save(Live.openNow(host, "끝난 방송", null, null, LocalDateTime.now()));
        ended.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        liveRepository.save(ended);

        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> errors = subscribeOnce(sender, "/user/queue/errors");

        sender.send("/app/lives/" + ended.getId() + "/reactions", Map.of("type", "CLAP"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L007");
    }

    @Test
    void 허용되지_않은_반응_종류는_거부된다() throws Exception {
        StompSession sender = connect(viewerToken);
        CompletableFuture<Map<String, Object>> errors = subscribeOnce(sender, "/user/queue/errors");

        // enum 에 없는 값은 역직렬화에서 null 이 된다. NPE(500)가 아니라 400 이어야 한다.
        sender.send("/app/lives/" + liveId + "/reactions", Map.of("type", "MIDDLE_FINGER"));

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("C001");
    }

    @Test
    void 초당_허용_횟수를_넘기면_거부되고_통과분만_브로드캐스트된다() throws Exception {
        StompSession sender = connect(viewerToken);
        List<Map<String, Object>> broadcasts =
                subscribeAll(sender, "/topic/lives/" + liveId + "/reactions");
        CompletableFuture<Map<String, Object>> errors = subscribeOnce(sender, "/user/queue/errors");

        // 허용은 창당 5건이다. 8건을 몰아 보내면 뒤쪽은 막혀야 한다.
        for (int i = 0; i < 8; i++) {
            sender.send("/app/lives/" + liveId + "/reactions", Map.of("type", "HEART"));
        }

        assertThat(errorCodeOf(errors.get(TIMEOUT_SECONDS, TimeUnit.SECONDS))).isEqualTo("L011");

        // 브로드캐스트가 모두 도착할 시간을 준 뒤 통과분을 센다.
        Thread.sleep(500);
        assertThat(new ArrayList<>(broadcasts)).hasSize(5);
    }
}
