package com.ssafy.backend.home.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * HOME-002 팔로잉 콘텐츠 조회 컨트롤러 테스트.
 *
 * <p>{@code /api/home/following}은 로그인 회원 전용이라 실제 시큐리티 필터 체인이 요청에 적용돼야
 * 인증/미인증 분기를 검증할 수 있어 {@link FilterChainProxy}를 끼운다. 인증 케이스는
 * {@link JwtTokenProvider}로 실제 Access Token을 발급해 보낸다(필터가 principal을 memberId(Long)로
 * 심으므로 문자열 principal을 세우는 {@code @WithMockUser}로는 컨트롤러의 캐스팅을 검증할 수 없다).
 */
@SpringBootTest
class FollowingControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        // Authorization 헤더 없이 접근 — /api/home/following 은 인증 필요.
        mockMvc.perform(get("/api/home/following"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 인증되면_팔로잉_콘텐츠를_반환한다() throws Exception {
        String token = jwtTokenProvider.createAccessToken(1L, "user@example.com");

        mockMvc.perform(get("/api/home/following").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.lives").isArray())
                .andExpect(jsonPath("$.data.products").isArray())
                .andExpect(jsonPath("$.data.empty").value(false))
                .andExpect(jsonPath("$.error").doesNotExist());
    }
}