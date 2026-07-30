package com.ssafy.backend.live.websocket;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.service.LiveViewerService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.lang.reflect.Type;
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
 * 시청자 수 실시간 집계 통합 테스트(-450).
 *
 * <p>실제 WebSocket 세션을 붙여 SUBSCRIBE·DISCONNECT 가 집계와 브로드캐스트로 이어지는지 본다 —
 * {@code LiveViewerServiceTest}가 집계 규칙 자체를 보고, 여기서는 <b>STOMP 이벤트가 그 규칙에
 * 실제로 연결돼 있는지</b>를 본다.
 *
 * <p><b>구독한 세션이 자기 구독으로 생긴 브로드캐스트를 받는지는 검증하지 않는다.</b>
 * {@code SessionSubscribeEvent} 발행과 브로커의 구독 등록은 경합한다. 그래서 먼저 붙은 세션이
 * <b>나중에 들어온 사람</b>의 변화를 받는 것으로 확인한다 — FE 계약도 초기값은 REST 로 받는 쪽이다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LiveViewerCountStompTest {

    private static final long TIMEOUT_SECONDS = 5;

    @LocalServerPort
    private int port;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private LiveViewerService liveViewerService;

    private WebSocketStompClient stompClient;
    private Long liveId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        Member host = memberRepository.save(Member.builder()
                .email("viewer-stomp-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("호스트")
                .build());
        liveId = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now())).getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    private StompSession connect() throws Exception {
        return stompClient
                .connectAsync(
                        "ws://localhost:" + port + "/ws",
                        new WebSocketHttpHeaders(),
                        new StompHeaders(),
                        new StompSessionHandlerAdapter() {})
                .get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
    }

    private BlockingQueue<Map<String, Object>> subscribeViewers(StompSession session)
            throws InterruptedException {
        BlockingQueue<Map<String, Object>> frames = new LinkedBlockingQueue<>();
        session.subscribe("/topic/lives/" + liveId + "/viewers", new StompFrameHandler() {
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

    /**
     * 앞서 쌓인 프레임을 버린다.
     *
     * <p><b>구독 자체가 브로드캐스트를 만든다.</b> 구독한 세션도 시청자 한 명이므로 "1명"
     * 프레임이 먼저 도착해 있을 수 있다. 그것을 비우지 않으면 다음 단계에서 기대하는 값 대신
     * 이 프레임을 읽는다.
     */
    private void drain(BlockingQueue<Map<String, Object>> frames) throws InterruptedException {
        Thread.sleep(500);
        frames.clear();
    }

    /** 기대하는 시청자 수가 담긴 프레임이 올 때까지 기다린다. 중간값 프레임은 지나친다. */
    private void awaitViewerCount(BlockingQueue<Map<String, Object>> frames, int expected)
            throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(TIMEOUT_SECONDS);
        while (System.nanoTime() < deadline) {
            Map<String, Object> frame = frames.poll(500, TimeUnit.MILLISECONDS);
            if (frame == null) {
                continue;
            }
            assertThat(frame.get("liveId")).isEqualTo(liveId.intValue());
            if (expected == (Integer) frame.get("viewerCount")) {
                return;
            }
        }
        throw new AssertionError("시청자 수 " + expected + " 프레임이 오지 않았다");
    }

    @Test
    void 구독하면_시청자로_집계된다() throws Exception {
        connect().subscribe("/topic/lives/" + liveId + "/chat", new StompSessionHandlerAdapter() {});
        Thread.sleep(500);

        // 채팅만 구독해도 그 방송을 보고 있는 것이다 — 시청자 수 토픽 구독자만 세면 실제보다 적다.
        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 나중에_들어온_시청자의_수가_먼저_붙은_세션에_브로드캐스트된다() throws Exception {
        StompSession first = connect();
        BlockingQueue<Map<String, Object>> frames = subscribeViewers(first);
        drain(frames);

        connect().subscribe("/topic/lives/" + liveId + "/chat", new StompSessionHandlerAdapter() {});

        awaitViewerCount(frames, 2);
    }

    @Test
    void 연결이_끊기면_시청자_수가_줄고_브로드캐스트된다() throws Exception {
        StompSession watcher = connect();
        BlockingQueue<Map<String, Object>> frames = subscribeViewers(watcher);

        StompSession leaving = connect();
        leaving.subscribe("/topic/lives/" + liveId + "/chat", new StompSessionHandlerAdapter() {});
        // 입장까지의 프레임(1명·2명)을 모두 비우고 퇴장만 본다.
        drain(frames);

        leaving.disconnect();

        awaitViewerCount(frames, 1);
        assertThat(liveViewerService.getViewerCount(liveId)).isEqualTo(1);
    }

    @Test
    void 최고_시청자_수가_DB에_기록된다() throws Exception {
        connect().subscribe("/topic/lives/" + liveId + "/chat", new StompSessionHandlerAdapter() {});
        connect().subscribe("/topic/lives/" + liveId + "/chat", new StompSessionHandlerAdapter() {});
        Thread.sleep(700);

        assertThat(liveRepository.findById(liveId).orElseThrow().getPeakViewerCount()).isEqualTo(2);
    }
}
