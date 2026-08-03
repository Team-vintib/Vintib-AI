package com.ssafy.backend.live.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
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
 * 소개 상품 전환 브로드캐스트 테스트(LIVE-004).
 *
 * <p>전환은 <b>REST로 받고 결과만 STOMP로 전파</b>한다. 호스트는 성공 여부를 즉시 알아야 하고,
 * 권한·편성 검증이 REST에서 훨씬 단순하기 때문이다.
 *
 * <p>그래서 이 테스트는 <b>REST 호출 → 토픽 수신</b>을 한 번에 확인한다. 컨트롤러 테스트가
 * 응답만 보고 브로드캐스트를 못 보므로, 시청자가 실제로 배지를 옮길 수 있는지는 여기서만 드러난다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LiveCurrentProductStompTest {

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
    private LiveProductRepository liveProductRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    private final HttpClient http = HttpClient.newHttpClient();
    private WebSocketStompClient stompClient;
    private String hostToken;
    private Long liveId;
    private Long productId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        // 온보딩 게이트(-475)를 통과해야 API 가 열린다. 미완료 회원은 U004 로 막힌다.
        Member host = Member.builder()
                .email("curation-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("호스트")
                .build();
        host.updateBasicInfo(
                "curation-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000002", "서울", "3층", null, Gender.MALE);
        host.completeOnboarding(MemberType.GENERAL);
        memberRepository.save(host);
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), host.getEmail());

        productId = productRepository.save(Product.builder()
                        .seller(host)
                        .categoryId(categoryRepository.findAll().get(0).getId())
                        .title("리바이스 501 빈티지")
                        .build())
                .getId();

        Live live = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        liveProductRepository.save(LiveProduct.link(live, productId, (short) 0, LocalDateTime.now()));
        liveId = live.getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    /** 비회원 시청자로 붙는다 — 배지는 로그인 여부와 무관하게 보여야 한다. */
    private BlockingQueue<Map<String, Object>> 시청자로_구독() throws Exception {
        StompSession session = stompClient
                .connectAsync(
                        "ws://localhost:" + port + "/ws",
                        new WebSocketHttpHeaders(),
                        new StompHeaders(),
                        new StompSessionHandlerAdapter() {})
                .get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        BlockingQueue<Map<String, Object>> frames = new LinkedBlockingQueue<>();
        session.subscribe("/topic/lives/" + liveId + "/product", new StompFrameHandler() {
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

    private int 소개_상품_변경(String productIdValue) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:" + port + "/api/lives/" + liveId + "/current-product"))
                .header("Authorization", "Bearer " + hostToken)
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5))
                .method("PATCH", HttpRequest.BodyPublishers.ofString(
                        "{\"productId\":%s}".formatted(productIdValue)))
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString()).statusCode();
    }

    @Test
    void 소개_상품을_바꾸면_시청자에게_전파된다() throws Exception {
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(소개_상품_변경(String.valueOf(productId))).isEqualTo(200);

        Map<String, Object> frame = frames.poll(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(frame).isNotNull();
        assertThat(frame.get("liveId")).isEqualTo(liveId.intValue());
        assertThat(frame.get("currentProductId")).isEqualTo(productId.intValue());
    }

    @Test
    void 해제하면_null이_전파된다() throws Exception {
        소개_상품_변경(String.valueOf(productId));
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(소개_상품_변경("null")).isEqualTo(200);

        Map<String, Object> frame = frames.poll(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(frame).isNotNull();
        // FE 는 이 값이 null 이면 NOW 배지를 아무 상품에도 달지 않는다.
        assertThat(frame.get("currentProductId")).isNull();
    }

    @Test
    void 검증에_실패하면_전파되지_않는다() throws Exception {
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        // 편성되지 않은 상품 — 404 로 거부돼야 하고, 시청자 화면은 그대로여야 한다.
        assertThat(소개_상품_변경("999999")).isEqualTo(404);

        assertThat(frames.poll(1, TimeUnit.SECONDS)).isNull();
    }
}
