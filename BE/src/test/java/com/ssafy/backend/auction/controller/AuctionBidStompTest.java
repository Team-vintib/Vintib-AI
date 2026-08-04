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
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.repository.PointAccountRepository;
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
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
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
 * 입찰 브로드캐스트, 그리고 <b>동시 입찰 경합</b> 테스트(AUCT-003~006).
 *
 * <p>후자가 이 계획의 핵심이다. 실제 서블릿 스레드 두 개가 같은 경매에 동시에 입찰을 던졌을 때
 * DB 행 잠금(`AuctionRepository.findByIdForUpdate`)이 실제로 직렬화하는지는 목(mock)으로는
 * 검증할 수 없다 — 그래서 {@code RANDOM_PORT} + 진짜 HTTP 스레드 두 개로 돌린다.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AuctionBidStompTest {

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

    @Autowired
    private PointAccountRepository pointAccountRepository;

    private final HttpClient http = HttpClient.newHttpClient();
    private WebSocketStompClient stompClient;
    private String hostToken;
    private Long liveId;
    private Long auctionId;

    @BeforeEach
    void setUp() {
        stompClient = new WebSocketStompClient(new StandardWebSocketClient());
        stompClient.setMessageConverter(new JacksonJsonMessageConverter());

        Member host = 회원("bid-host");
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

        Auction auction = auctionRepository.save(
                Auction.configure(live, product.getId(), 10_000L, 1_000L, 60));
        auction.start(LocalDateTime.now());
        auctionId = auctionRepository.save(auction).getId();
    }

    @AfterEach
    void tearDown() {
        stompClient.stop();
    }

    private Member 회원(String prefix) {
        Member member = Member.builder()
                .email(prefix + "-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("회원")
                .build();
        member.updateBasicInfo(
                prefix + "-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000005", "서울", "6층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        return memberRepository.save(member);
    }

    private String 회원_토큰(String prefix, long pointBalance) {
        Member member = 회원(prefix);
        PointAccount account = PointAccount.builder().member(member).build();
        account.charge(pointBalance);
        pointAccountRepository.save(account);
        return jwtTokenProvider.createAccessToken(member.getId(), member.getEmail());
    }

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
        Thread.sleep(300);
        return frames;
    }

    private HttpResponse<String> 입찰(String token, long amount) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:" + port + "/api/auctions/" + auctionId + "/bids"))
                .header("Authorization", "Bearer " + token)
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5))
                .POST(HttpRequest.BodyPublishers.ofString("{\"amount\":%d}".formatted(amount)))
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString());
    }

    @Test
    @SuppressWarnings("unchecked")
    void 입찰하면_시청자에게_현황과_함께_전파된다() throws Exception {
        String bidderToken = 회원_토큰("watcher-bidder", 100_000L);
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        assertThat(입찰(bidderToken, 10_000L).statusCode()).isEqualTo(200);

        Map<String, Object> frame = frames.poll(TIMEOUT_SECONDS, TimeUnit.SECONDS);

        assertThat(frame).isNotNull();
        assertThat(frame.get("type")).isEqualTo("BID_PLACED");
        Map<String, Object> auction = (Map<String, Object>) frame.get("auction");
        assertThat(auction.get("currentPrice")).isEqualTo(10_000);
        assertThat(auction.get("bidCount")).isEqualTo(1);
    }

    @Test
    void 입찰이_실패하면_아무것도_전파되지_않는다() throws Exception {
        String bidderToken = 회원_토큰("fail-bidder", 100_000L);
        BlockingQueue<Map<String, Object>> frames = 시청자로_구독();

        // 다음 입찰가(10,000원)가 아닌 값 — 거부돼야 한다.
        assertThat(입찰(bidderToken, 999L).statusCode()).isEqualTo(400);

        assertThat(frames.poll(1, TimeUnit.SECONDS)).isNull();
    }

    /**
     * <b>동시 입찰 경합.</b> 서로 다른 두 회원이 <b>같은 순간에 같은 금액(정확한 시작가)</b>으로
     * 입찰을 쏜다. {@code CountDownLatch}로 두 스레드를 최대한 같은 시점에 풀어 실제 경합을
     * 유도한다.
     *
     * <p>DB 행 잠금이 제대로 동작한다면 <b>정확히 하나만 성공</b>해야 한다 — 잠금이 없다면
     * 둘 다 "현재가가 0"인 상태를 동시에 읽어 둘 다 통과하거나(유효성 검증 우회), 최소한
     * {@code current_price}·{@code bid_held}가 두 번 반영돼 정합성이 깨진다.
     */
    @Test
    void 동시에_같은_금액으로_입찰하면_하나만_성공한다() throws Exception {
        String tokenA = 회원_토큰("racer-a", 100_000L);
        String tokenB = 회원_토큰("racer-b", 100_000L);

        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch go = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            var futureA = pool.submit(() -> {
                ready.countDown();
                go.await();
                return 입찰(tokenA, 10_000L);
            });
            var futureB = pool.submit(() -> {
                ready.countDown();
                go.await();
                return 입찰(tokenB, 10_000L);
            });

            ready.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
            go.countDown(); // 두 스레드를 동시에 풀어준다.

            List<Integer> statusCodes = List.of(
                    futureA.get(TIMEOUT_SECONDS, TimeUnit.SECONDS).statusCode(),
                    futureB.get(TIMEOUT_SECONDS, TimeUnit.SECONDS).statusCode());

            long succeeded = statusCodes.stream().filter(code -> code == 200).count();
            long failed = statusCodes.stream().filter(code -> code == 400).count();

            assertThat(succeeded).isEqualTo(1);
            assertThat(failed).isEqualTo(1);

            // 최종 상태도 "정확히 한 번의 입찰"만 반영돼야 한다 — 두 번 반영되면 20,000원이 된다.
            Auction reloaded = auctionRepository.findById(auctionId).orElseThrow();
            assertThat(reloaded.getCurrentPrice()).isEqualTo(10_000L);
        } finally {
            pool.shutdownNow();
        }
    }
}
