package com.ssafy.backend.auction.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
import java.time.LocalDateTime;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * AUCT-001 경매 조건 설정 컨트롤러 테스트.
 *
 * <p>Bean Validation(400)과 인증(401)은 서비스 단위 테스트로는 확인되지 않아 실제 필터 체인을 끼운다.
 * 상품·라이브·연결은 FK 제약이 있어 실제 행을 저장해 두고 시작한다.
 *
 * <p>요청 본문은 {@code ObjectMapper} 없이 직접 만든다 — Spring Boot 4 모듈러 테스트 컨텍스트에는
 * {@code ObjectMapper} 빈이 올라오지 않는다.
 */
@SpringBootTest
class AuctionControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

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
    private PointAccountRepository pointAccountRepository;

    private MockMvc mockMvc;
    private String hostToken;
    private Member hostMember;
    private Long liveId;
    private Long linkedProductId;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        String email = "auction-host-" + UUID.randomUUID() + "@example.com";
        Member host = Member.builder()
                .email(email)
                .password("encoded")
                .name("호스트")
                .build();
        // SY019 게이트: 온보딩 미완료 회원은 경매 설정 등 다른 기능을 쓸 수 없다.
        // 닉네임은 unique 제약이 있어 매 테스트마다 겹치지 않게 만든다.
        String nickname = "host-" + UUID.randomUUID().toString().substring(0, 8);
        host.updateBasicInfo(nickname, "01000000000", "서울", "1층", null, Gender.MALE);
        host.completeOnboarding(MemberType.GENERAL);
        host = memberRepository.save(host);
        hostMember = host;
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), email);

        // 카테고리는 필수다(PROD-001). 시드된 마스터에서 아무거나 하나 집는다 — 경매 검증에
        // 카테고리 값 자체는 무관하고, NOT NULL 제약만 만족시키면 된다.
        Product product = productRepository.save(Product.builder()
                .seller(host)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title("리바이스 501 빈티지")
                .build());
        linkedProductId = product.getId();

        Live live = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        liveId = live.getId();
        liveProductRepository.save(LiveProduct.link(live, linkedProductId, (short) 0, LocalDateTime.now()));
    }

    /** 입찰 가능한 잔액을 쥔 신규 회원 토큰을 만든다. */
    private String 회원_토큰(long pointBalance) {
        String email = "auction-bidder-" + UUID.randomUUID() + "@example.com";
        Member member = Member.builder().email(email).password("encoded").name("입찰자").build();
        String nickname = "bidder-" + UUID.randomUUID().toString().substring(0, 8);
        member.updateBasicInfo(nickname, "01000000001", "서울", "2층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        member = memberRepository.save(member);

        PointAccount account = PointAccount.builder().member(member).build();
        account.charge(pointBalance);
        pointAccountRepository.save(account);

        return jwtTokenProvider.createAccessToken(member.getId(), email);
    }

    private String bidRequestBody(long amount) {
        return """
                {"amount":%d}
                """.formatted(amount);
    }

    /** 조건 설정 → 시작까지 마친 경매 ID. 시작가 10,000원, 증액 단위 1,000원. */
    private Long 진행_중인_경매_ID() throws Exception {
        Long auctionId = 설정된_경매_ID();
        mockMvc.perform(post("/api/auctions/{auctionId}/start", auctionId)
                .header("Authorization", "Bearer " + hostToken)).andExpect(status().isOk());
        return auctionId;
    }

    private String configRequestBody(Long productId, Long startPrice, Long bidUnit, Integer durationSeconds) {
        return """
                {"productId":%d,"startPrice":%d,"bidUnit":%d,"durationSeconds":%d}
                """.formatted(productId, startPrice, bidUnit, durationSeconds);
    }

    @Test
    void 연결된_상품에_조건을_설정하면_201과_READY를_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 60)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("READY"))
                .andExpect(jsonPath("$.data.currentPrice").value(0))
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 증액_단위가_0이면_400을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 0L, 60)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    void 진행_시간이_0이면_400을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 0)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 라이브에_연결되지_않은_상품이면_404를_반환한다() throws Exception {
        long 연결되지_않은_상품 = linkedProductId + 999_999L;

        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(연결되지_않은_상품, 10_000L, 1_000L, 60)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L006"));
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 60)))
                .andExpect(status().isUnauthorized());
    }

    // ---------- 현황 조회·시작 (AUCT-002) ----------

    /** 조건을 설정하고 만들어진 경매 ID 를 돌려준다. */
    private Long 설정된_경매_ID() throws Exception {
        String body = mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(linkedProductId, 10_000L, 1_000L, 60)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();
        // ObjectMapper 빈이 테스트 컨텍스트에 없어(모듈러 스타터) 필요한 값만 뽑아 쓴다.
        return Long.parseLong(body.replaceAll(".*\"id\":(\\d+).*", "$1"));
    }

    @Test
    void 경매가_없는_라이브의_현황은_200과_null이다() throws Exception {
        // 아직 경매를 걸지 않은 방송이 정상이다. 404 로 만들면 시청자 진입마다 에러가 뜬다.
        mockMvc.perform(get("/api/lives/{liveId}/auctions/current", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void 비회원도_경매_현황을_조회할_수_있다() throws Exception {
        설정된_경매_ID();

        mockMvc.perform(get("/api/lives/{liveId}/auctions/current", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("READY"))
                .andExpect(jsonPath("$.data.productTitle").value("리바이스 501 빈티지"))
                // 첫 입찰은 시작가 그대로다.
                .andExpect(jsonPath("$.data.nextBidPrice").value(10_000))
                .andExpect(jsonPath("$.data.bidCount").value(0))
                .andExpect(jsonPath("$.data.serverNow").isNotEmpty());
    }

    @Test
    void 호스트가_경매를_시작하면_RUNNING과_종료_예정_시각이_내려온다() throws Exception {
        Long auctionId = 설정된_경매_ID();

        mockMvc.perform(post("/api/auctions/{auctionId}/start", auctionId)
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("RUNNING"))
                .andExpect(jsonPath("$.data.startedAt").isNotEmpty())
                .andExpect(jsonPath("$.data.endsAt").isNotEmpty());
    }

    @Test
    void 시작한_경매는_현황_조회에서_준비_중_경매보다_먼저_나온다() throws Exception {
        Long first = 설정된_경매_ID();
        mockMvc.perform(post("/api/auctions/{auctionId}/start", first)
                .header("Authorization", "Bearer " + hostToken)).andExpect(status().isOk());

        mockMvc.perform(get("/api/lives/{liveId}/auctions/current", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.auctionId").value(first.intValue()))
                .andExpect(jsonPath("$.data.status").value("RUNNING"));
    }

    @Test
    void 이미_시작한_경매를_다시_시작하면_400이다() throws Exception {
        Long auctionId = 설정된_경매_ID();
        mockMvc.perform(post("/api/auctions/{auctionId}/start", auctionId)
                .header("Authorization", "Bearer " + hostToken)).andExpect(status().isOk());

        mockMvc.perform(post("/api/auctions/{auctionId}/start", auctionId)
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("A006"));
    }

    @Test
    void 진행_중인_경매가_있으면_다른_경매를_시작할_수_없다() throws Exception {
        // 한 라이브에서 동시에 진행 중인 경매는 1개다(LIVE-004).
        Long first = 설정된_경매_ID();
        mockMvc.perform(post("/api/auctions/{auctionId}/start", first)
                .header("Authorization", "Bearer " + hostToken)).andExpect(status().isOk());

        Product another = productRepository.save(Product.builder()
                .seller(hostMember)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title("두 번째 상품")
                .build());
        liveProductRepository.save(LiveProduct.link(
                liveRepository.findById(liveId).orElseThrow(), another.getId(), (short) 1, LocalDateTime.now()));

        String body = mockMvc.perform(post("/api/lives/{liveId}/auctions", liveId)
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(another.getId(), 5_000L, 500L, 30)))
                .andReturn().getResponse().getContentAsString();
        Long second = Long.parseLong(body.replaceAll(".*\"id\":(\\d+).*", "$1"));

        mockMvc.perform(post("/api/auctions/{auctionId}/start", second)
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("A007"));
    }

    @Test
    void 경매_시작은_미인증이면_401이다() throws Exception {
        Long auctionId = 설정된_경매_ID();

        mockMvc.perform(post("/api/auctions/{auctionId}/start", auctionId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 존재하지_않는_경매를_시작하면_404다() throws Exception {
        mockMvc.perform(post("/api/auctions/{auctionId}/start", 999_999_999L)
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("A005"));
    }

    // ---------- 입찰 (AUCT-003~006) ----------

    @Test
    void 시작가로_입찰하면_현재가와_최고_입찰자가_갱신된다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(100_000L);

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.currentPrice").value(10_000))
                .andExpect(jsonPath("$.data.nextBidPrice").value(11_000))
                .andExpect(jsonPath("$.data.bidCount").value(1));
    }

    @Test
    void 상위_입찰이_들어오면_직전_최고_입찰자의_입찰이_밀린다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String first = 회원_토큰(100_000L);
        String second = 회원_토큰(100_000L);

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + first)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk());

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + second)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(11_000L)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.currentPrice").value(11_000))
                .andExpect(jsonPath("$.data.bidCount").value(2));
    }

    @Test
    void 다음_입찰가와_다른_금액을_보내면_400이다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(100_000L);

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(50_000L)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("A008"));
    }

    @Test
    void 직전_최고_입찰자_본인은_연속으로_입찰하면_400이다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(100_000L);

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk());

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(11_000L)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("A009"));
    }

    @Test
    void 잔액이_부족하면_400이다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String poorBidderToken = 회원_토큰(5_000L); // 시작가(10,000원)보다 적다

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + poorBidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("W001"));
    }

    @Test
    void 다른_경매에_이미_최고_입찰자면_409다() throws Exception {
        // AUCT-009 — 최고 입찰자인 동안 다른 경매에 입찰할 수 없다.
        Long firstAuctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(1_000_000L);
        mockMvc.perform(post("/api/auctions/{auctionId}/bids", firstAuctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk());

        Product secondProduct = productRepository.save(Product.builder()
                .seller(hostMember)
                .categoryId(categoryRepository.findAll().get(0).getId())
                .title("두 번째 상품")
                .build());
        Live secondLive = liveRepository.save(
                Live.openNow(hostMember, "다른 방송", null, null, LocalDateTime.now()));
        liveProductRepository.save(
                LiveProduct.link(secondLive, secondProduct.getId(), (short) 0, LocalDateTime.now()));
        String body = mockMvc.perform(post("/api/lives/{liveId}/auctions", secondLive.getId())
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(configRequestBody(secondProduct.getId(), 5_000L, 500L, 60)))
                .andReturn().getResponse().getContentAsString();
        Long secondAuctionId = Long.parseLong(body.replaceAll(".*\"id\":(\\d+).*", "$1"));
        mockMvc.perform(post("/api/auctions/{auctionId}/start", secondAuctionId)
                .header("Authorization", "Bearer " + hostToken)).andExpect(status().isOk());

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", secondAuctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(5_000L)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("A011"));
    }

    @Test
    void 진행_중이_아닌_경매에_입찰하면_400이다() throws Exception {
        Long auctionId = 설정된_경매_ID(); // READY, 아직 시작 전
        String bidderToken = 회원_토큰(100_000L);

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("A001"));
    }

    @Test
    void 입찰은_미인증이면_401이다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();

        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 입찰_내역이_최신순으로_조회되고_본인_여부가_표시된다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(100_000L);
        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(1))
                .andExpect(jsonPath("$.data.content[0].amount").value(10_000))
                .andExpect(jsonPath("$.data.content[0].isMine").value(true));
    }

    @Test
    void 비회원도_입찰_내역을_조회할_수_있다() throws Exception {
        Long auctionId = 진행_중인_경매_ID();
        String bidderToken = 회원_토큰(100_000L);
        mockMvc.perform(post("/api/auctions/{auctionId}/bids", auctionId)
                        .header("Authorization", "Bearer " + bidderToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bidRequestBody(10_000L)))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/auctions/{auctionId}/bids", auctionId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content[0].isMine").value(false));
    }

    @Test
    void 존재하지_않는_경매의_입찰_내역을_조회하면_404다() throws Exception {
        mockMvc.perform(get("/api/auctions/{auctionId}/bids", 999_999_999L))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("A005"));
    }
}