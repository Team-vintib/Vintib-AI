package com.ssafy.backend.home.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
 */
@SpringBootTest
class HomeControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private com.ssafy.backend.auth.jwt.JwtTokenProvider jwtTokenProvider;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();
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
    void 진행_중_라이브_카드에_방송_상태가_담긴다() throws Exception {
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.liveNow[0].broadcastStatus").value("LIVE"));
    }

    @Test
    void 경매_예정_상품은_경매예정_플래그로_내려간다() throws Exception {
        // 경매 예정 상품은 가격 대신 auctionScheduled=true 로 표시한다(HOME-001 정책).
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].auctionScheduled").value(true))
                .andExpect(jsonPath("$.data.upcomingAuctionProducts[0].sellType").value("AUCTION_SCHEDULED"));
    }

    @Test
    void 비회원도_홈_콘텐츠를_조회할_수_있다() throws Exception {
        // Authorization 헤더 없이도 200 — /api/home 은 SecurityConfig PUBLIC_ENDPOINTS.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk());
    }

    @Test
    void 상품_카드에_판매자명과_카테고리명이_담긴다() throws Exception {
        // FE 가 "판매자 정보 확인 중" 으로 때우던 자리(FE 요청 009-home-card-response-fields).
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
        String token = jwtTokenProvider.createAccessToken(1L, "user@example.com");

        mockMvc.perform(get("/api/home").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.onSaleProducts[0].isWished").isBoolean());
    }

    @Test
    void 카테고리별_상품_탭_섹션이_카테고리_마스터를_따른다() throws Exception {
        // 탭 구성은 카테고리 마스터(SY007) 최상위 6개. FE 요청서의 '원피스'는 시드에 없어 '가방'으로 대체.
        mockMvc.perform(get("/api/home"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.categoryProductSections").isArray())
                .andExpect(jsonPath("$.data.categoryProductSections.length()").value(6))
                .andExpect(jsonPath("$.data.categoryProductSections[0].title").value("아우터"))
                .andExpect(jsonPath("$.data.categoryProductSections[0].products.length()").value(3));
    }
}