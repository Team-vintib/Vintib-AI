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
}