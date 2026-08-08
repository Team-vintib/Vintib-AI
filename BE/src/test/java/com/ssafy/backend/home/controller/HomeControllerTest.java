package com.ssafy.backend.home.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auction.entity.Auction;
import com.ssafy.backend.auction.repository.AuctionRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * HOME-001 홈 콘텐츠 조회 컨트롤러 테스트.
 *
 * <p>기존 {@code HealthControllerIntegrationTest}와 동일하게 전체 컨텍스트를 띄우고
 * {@code WebApplicationContext}에서 MockMvc를 구성한다(Spring Boot 4 모듈러 테스트 스타터에는
 * {@code @AutoConfigureMockMvc}가 없다). 다만 {@code /api/home}가 비회원 공개인지 검증하려면
 * 실제 시큐리티 필터 체인이 요청에 적용돼야 하므로 {@link FilterChainProxy}를 함께 끼운다.
 *
 * <p><b>홈이 Mock을 벗고 실데이터가 되면서 테스트도 실제 행을 심는다.</b> 예전에는 아무것도
 * 심지 않아도 하드코딩된 카드가 나왔는데, 바로 그 탓에 존재하지 않는 라이브가 홈에 뜨는
 * 정합성 버그가 있었다. 이제는 <b>심은 것만 나오는지</b>를 본다.
 */
@SpringBootTest
class HomeControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private com.ssafy.backend.auth.jwt.JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private AuctionRepository auctionRepository;

    private MockMvc mockMvc;
    private Member seller;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        seller = memberRepository.save(회원("빈티지장인"));

        // 홈은 "최신순 앞에서 N개"라, 테스트마다 새로 심은 것이 반드시 앞에 오게 된다.
        // 실제 상품은 탭(depth=2)이 아니라 그 아래 소분류(depth=3)에 걸린다 — 탭 자신의
        // id를 쓰면 카테고리 탭 섹션 재귀 수집 버그를 테스트가 가려버린다.
        Long categoryId = 첫_번째_탭의_소분류().getId();
        Product 상시판매 = Product.builder()
                .seller(seller)
                .categoryId(categoryId)
                .title("리바이스 501 빈티지")
                .build();
        // 빌더는 DRAFT 로 만든다 — 판매 방식을 정해야 홈에 나온다.
        // 상태를 바꾼 뒤 다시 save 해야 반영된다(save 가 돌려준 엔티티는 이미 준영속이다).
        상시판매.registerDirectSale(45_000L);
        productRepository.save(상시판매);

        Product 경매예정 = Product.builder()
                .seller(seller)
                .categoryId(categoryId)
                .title("버버리 노바체크 트렌치")
                .build();
        경매예정.scheduleAuction();
        경매예정 = productRepository.save(경매예정);

        Live 진행중 = liveRepository.save(
                Live.openNow(seller, "빈티지 데님 라이브", null, null, LocalDateTime.now()));
        liveRepository.save(Live.schedule(
                seller, "주말 아메카지 특집", null, null, LocalDateTime.now().plusDays(2)));

        // 경매 예정 카드의 시작가·시작 예정 시각은 이 경매(와 그 방송)에서 나온다.
        auctionRepository.save(Auction.configure(진행중, 경매예정.getId(), 50_000L, 5_000L, 60));
    }

    /**
     * 카테고리 탭은 옷 종류 대분류(depth=2, 아우터/상의/... )를 따른다. 시드 순서가
     * 바뀌어도 깨지지 않게 이름을 박지 않고 마스터에서 첫 탭을 가져온다.
     */
    private Category 첫_번째_탭() {
        return categoryRepository.findAllByOrderByIdAsc().stream()
                .filter(category -> category.getDepth() == 2)
                .findFirst()
                .orElseThrow();
    }

    /** 첫 탭 바로 아래 소분류(depth=3) 하나 — 실제 상품이 걸리는 자리다. */
    private Category 첫_번째_탭의_소분류() {
        Long tabId = 첫_번째_탭().getId();
        return categoryRepository.findAllByOrderByIdAsc().stream()
                .filter(category -> Objects.equals(category.getParentId(), tabId))
                .findFirst()
                .orElseThrow();
    }

    private Member 회원(String nicknamePrefix) {
        Member member = Member.builder()
                .email("home-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("판매자")
                .build();
        // SY019 게이트: 온보딩 미완료 회원은 인증이 필요한 요청에서 U004로 막힌다.
        member.updateBasicInfo(
                nicknamePrefix + "-" + UUID.randomUUID().toString().substring(0, 8),
                "01000000000", "서울", "1층", null, Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        return member;
    }

    @Test
    void 홈_콘텐츠를_섹션별로_반환한다() throws Exception {
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.liveNow").isArray())
                .andExpect(jsonPath("$.data.scheduledLives").isArray())
                .andExpect(jsonPath("$.data.onSaleProducts").isArray())
                .andExpect(jsonPath("$.data.upcomingAuctionProducts").isArray())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 진행_중_라이브_카드에_방송_상태와_호스트_ID가_담긴다() throws Exception {
        // hostId 는 카드에서 판매자 프로필로 이동하는 데 쓴다.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.liveNow[0].broadcastStatus").value("LIVE"))
                .andExpect(jsonPath("$.data.liveNow[0].hostId").isNumber());
    }

    @Test
    void 종료된_방송은_홈에_노출되지_않는다() throws Exception {
        // 홈만 종료 라이브를 "진행 중"으로 내려 카드를 누르면 404가 났다.
        Live 종료된_방송 = liveRepository.save(
                Live.openNow(seller, "이미 끝난 방송", null, null, LocalDateTime.now()));
        종료된_방송.transitionTo(com.ssafy.backend.live.entity.LiveStatus.ENDED, LocalDateTime.now());
        liveRepository.save(종료된_방송);

        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.liveNow[?(@.liveId == %d)]".formatted(종료된_방송.getId()))
                        .isEmpty());
    }

    @Test
    void 경매_예정_상품은_경매예정_플래그로_내려간다() throws Exception {
        // 경매 예정 상품은 가격 대신 auctionScheduled=true 로 표시한다(HOME-001 정책).
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].auctionScheduled").value(true))
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].sellType").value("AUCTION_SCHEDULED"))
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].price").doesNotExist());
    }

    @Test
    void 비회원도_홈_콘텐츠를_조회할_수_있다() throws Exception {
        // Authorization 헤더 없이도 200 — /api/home 은 SecurityConfig PUBLIC_ENDPOINTS.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk());
    }

    @Test
    void 상품_카드에_판매자명과_카테고리명이_담긴다() throws Exception {
        // FE 가 "판매자 정보 확인 중" 으로 때우던 자리.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.onSaleProducts[0].sellerName").isNotEmpty())
                .andExpect(jsonPath("$.data.onSaleProducts[0].categoryName").isNotEmpty());
    }

    @Test
    void 경매_예정_상품에_시작가와_경매_시작_시각이_담긴다() throws Exception {
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].startingBid").isNumber())
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].auctionStartsAt").isNotEmpty());
    }

    @Test
    void 진행_중_라이브에는_시작_시각이_예약_라이브에는_예정_시각이_담긴다() throws Exception {
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.liveNow[0].startedAt").isNotEmpty())
                .andExpect(jsonPath("$.data.liveNow[0].scheduledAt").doesNotExist())
                .andExpect(jsonPath("$.data.scheduledLives[0].scheduledAt").isNotEmpty())
                .andExpect(jsonPath("$.data.scheduledLives[0].startedAt").doesNotExist());
    }

    @Test
    void 비회원_요청이면_찜_여부가_null로_내려간다() throws Exception {
        // false 로 내리면 FE 가 "찜 해제 가능" 으로 오해한다. 모른다는 뜻은 null 로 구분한다.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.onSaleProducts[0].isWished").doesNotExist());
    }

    @Test
    void 로그인_요청이면_찜_여부가_채워진다() throws Exception {
        String token = jwtTokenProvider.createAccessToken(seller.getId(), seller.getEmail());

        mockMvc.perform(get("/api/home").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.onSaleProducts[0].isWished").isBoolean());
    }

    @Test
    void 카테고리별_상품_탭_섹션이_카테고리_마스터를_따른다() throws Exception {
        // 탭 구성은 카테고리 마스터(SY007)의 옷 종류 대분류(depth=2) 6개. 이름은 마스터를
        // 그대로 따라가므로 하드코딩하지 않고 실제 첫 탭과 맞는지만 본다.
        List<Category> tabs = categoryRepository.findAllByOrderByIdAsc().stream()
                .filter(category -> category.getDepth() == 2)
                .toList();

        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.categoryProductSections").isArray())
                .andExpect(jsonPath("$.data.categoryProductSections.length()")
                        .value(Math.min(6, tabs.size())))
                .andExpect(jsonPath("$.data.categoryProductSections[0].title")
                        .value(tabs.get(0).getName()));
    }

    @Test
    void 소분류에_걸린_상품도_탭_섹션에_재귀적으로_묶인다() throws Exception {
        // 028 — 상품은 탭 자신(depth=2)이 아니라 그 아래 소분류(depth=3)에 걸린다. 탭의 직계
        // 자식만 모으면 이 상품이 어느 섹션에도 잡히지 않아 항상 빈 배열이 됐다.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.categoryProductSections[0].products[?(@.name == '리바이스 501 빈티지')]")
                        .isNotEmpty());
    }
}