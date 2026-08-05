package com.ssafy.backend.auction.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.repository.AuctionRepository;
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
 * 경매 시작 브로드캐스트 테스트(AUCT-002, FE 요청 009 §3.3).
 *
 * <p>경매 시작은 <b>REST 로 받고 결과만 STOMP 로 전파</b>한다 — 호스트는 성공 여부를 즉시 알아야
 * 하고, 권한·상태 검증이 REST 에서 훨씬 단순하다. 컨트롤러 테스트는 응답만 보고 브로드캐스트를
 * 못 보므로, <b>시청자가 실제로 경매 시작을 알아채는지는 여기서만 드러난다.</b>
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AuctionStartStompTest {

    private static final long TIMEOUT_SECONDS = 5;

    @LocalServerPort
    private int port;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private LiveProductRepository liveProductRepository;

    @Autowired
    private AuctionRepository auctionRepository;

    private final HttpClient http = HttpClient.newHttpClient();
    private WebSocketStompClient stompClient;
    private String hostToken;
    private Long liveId;
    private Long auctionId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        // 온보딩 게이트(-475)를 통과해야 API 가 열린다.
        Member host = Member.builder()
                .email("auction-stomp-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("호스트")
                .build();
        host.updateBasicInfo(
                "auct-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000004", "서울", "5층", null, Gender.MALE);
        host.completeOnboarding(MemberType.GENERAL);
        memberRepository.save(host);
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), host.getEmail());

        Product product = productRepository.save(Product.builder()
                .seller(host)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title("리바이스 501 빈티지")
                .build());

        Live live = liveRepository.save(
                Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        liveId = live.getId();
        liveProductRepository.save(
                LiveProduct.link(live, product.getId(), (short) 0, LocalDateTime.now()));

        auctionId = auctionRepository.save(
                        Auction.configure(live, product.getId(), 10_000L, 1_000L, 60))
                .getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    /** 비회원 시청자로 붙는다 — 경매가 시작됐다는 사실은 로그인 여부와 무관하게 보여야 한다. */
    private BlockingQueue<Map<String, Object>> 시청자로_구독() throws Exception {
        StompSession session = stompClient
                .connectAsync(
                        "ws://localhost:" + port + "/ws",
                        new WebSocketHttpHeaders(),
                        new StompHeaders(),
                        new StompSessionHandlerAdapter() {})
                .get(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        BlockingQueue<Map<String, Object>> frames = new LinkedBlockingQueue<>();
        session.subscribe("/topic/lives/" + liveId + "/auctions", new StompFrameHandler() {
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

    private int 경매_시작(Long targetAuctionId) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:" + port + "/api/auctions/" + targetAuctionId + "/start"))
                .header("Authorization", "Bearer " + hostToken)
                .timeout(Duration.ofSeconds(5))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString()).statusCode();
    }

    @Test
    @SuppressWarnings("unchecked")
    void 경매를_시작하면_시청자에게_현황과_함께_전파된다() throws Exception {
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(경매_시작(auctionId)).isEqualTo(200);

        Map<String, Object> frame = frames.poll(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(frame).isNotNull();
        assertThat(frame.get("type")).isEqualTo("AUCTION_STARTED");

        // 변화분이 아니라 현황 전체를 싣는다 — 프레임을 하나 놓친 클라이언트도 따라잡을 수 있어야 한다.
        Map<String, Object> auction = (Map<String, Object>) frame.get("auction");
        assertThat(auction.get("auctionId")).isEqualTo(auctionId.intValue());
        assertThat(auction.get("status")).isEqualTo("RUNNING");
        assertThat(auction.get("endsAt")).isNotNull();
        // 첫 입찰은 시작가 그대로다.
        assertThat(auction.get("nextBidPrice")).isEqualTo(10_000);
    }

    @Test
    void 시작에_실패하면_아무것도_전파되지_않는다() throws Exception {
        // 존재하지 않는 경매다. 실패했는데 시청자 화면만 시작된 것처럼 바뀌면 안 된다.
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(경매_시작(999_999_999L)).isEqualTo(404);

        assertThat(frames.poll(1, TimeUnit.SECONDS)).isNull();
    }
}
