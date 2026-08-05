package com.ssafy.backend.live.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import java.lang.reflect.Type;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
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
 * 방송 상태 전이 브로드캐스트 테스트(FE 요청 013).
 *
 * <p><b>이게 없으면 호스트가 종료해도 시청자 화면은 그대로 남는다</b> — 새로고침해야 404를
 * 만난다. 컨트롤러 테스트는 응답만 보고 브로드캐스트를 못 보므로, 시청자가 실제로 종료를
 * 알아채는지는 여기서만 드러난다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LiveStatusStompTest {

    private static final long TIMEOUT_SECONDS = 5;

    @LocalServerPort
    private int port;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    private final HttpClient http = HttpClient.newHttpClient();
    private WebSocketStompClient stompClient;
    private String hostToken;
    private Long liveId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        // 온보딩 게이트(-475)를 통과해야 API 가 열린다. 미완료 회원은 U004 로 막힌다.
        Member host = Member.builder()
                .email("live-status-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("호스트")
                .build();
        host.updateBasicInfo(
                "status-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000003", "서울", "4층", null, Gender.MALE);
        host.completeOnboarding(MemberType.GENERAL);
        memberRepository.save(host);
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), host.getEmail());

        liveId = liveRepository.save(
                        Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()))
                .getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    /** 비회원 시청자로 붙는다 — 종료 안내는 로그인 여부와 무관하게 받아야 한다. */
    private BlockingQueue<Map<String, Object>> 시청자로_구독() throws Exception {
        StompSession session = stompClient
                .connectAsync(
                        "ws://localhost:" + port + "/ws",
                        new WebSocketHttpHeaders(),
                        new StompHeaders(),
                        new StompSessionHandlerAdapter() {})
                .get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        BlockingQueue<Map<String, Object>> frames = new LinkedBlockingQueue<>();
        session.subscribe("/topic/lives/" + liveId + "/status", new StompFrameHandler() {
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
        // 구독이 반영되기 전에 발행하면 브로드캐스트를 놓친다.
        Thread.sleep(300);
        return frames;
    }

    private int 상태_전이(String status) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:" + port + "/api/lives/" + liveId + "/status"))
                .header("Authorization", "Bearer " + hostToken)
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5))
                .method("PATCH", HttpRequest.BodyPublishers.ofString(
                        "{\"status\":\"%s\"}".formatted(status)))
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString()).statusCode();
    }

    @Test
    void 방송을_종료하면_시청자에게_전파된다() throws Exception {
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(상태_전이("ENDED")).isEqualTo(200);

        Map<String, Object> frame = frames.poll(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(frame).isNotNull();
        assertThat(frame.get("liveId")).isEqualTo(liveId.intValue());
        assertThat(frame.get("status")).isEqualTo("ENDED");
        // 종료 시각이 있어야 FE 가 "몇 시에 끝난 방송"인지 안내할 수 있다.
        assertThat(frame.get("endedAt")).isNotNull();
    }

    @Test
    void 전이가_거부되면_아무것도_전파되지_않는다() throws Exception {
        // 진행 중인 방송은 다시 LIVE 로 갈 수 없다. 실패했는데 시청자 화면만 바뀌면 안 된다.
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(상태_전이("LIVE")).isEqualTo(400);

        assertThat(frames.poll(1, TimeUnit.SECONDS)).isNull();
    }
}
