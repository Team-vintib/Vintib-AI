package com.ssafy.backend.live.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
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
 * LIVE-001 예약 라이브 개설 컨트롤러 테스트.
 *
 * <p>개설은 로그인 회원 전용이라 실제 시큐리티 필터 체인을 끼우고 {@link JwtTokenProvider}로
 * 실제 토큰을 발급한다(필터가 principal을 memberId(Long)로 심는다). 호스트는 FK 제약이 있어
 * 실제 회원 행이 필요하므로 테스트마다 새 회원을 저장한다 — 이메일이 유니크라 UUID로 겹침을 피한다.
 *
 * <p>요청 본문은 {@code ObjectMapper} 없이 직접 만든다 — Spring Boot 4 모듈러 테스트 컨텍스트에는
 * {@code ObjectMapper} 빈이 올라오지 않는다.
 */
@SpringBootTest
class LiveControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    private MockMvc mockMvc;
    private String hostToken;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        String email = "live-host-" + UUID.randomUUID() + "@example.com";
        Member host = memberRepository.save(Member.builder()
                .email(email)
                .password("encoded")
                .name("호스트")
                .build());
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), email);
    }

    private String scheduleRequestBody(String title, String thumbnailUrl, LocalDateTime scheduledAt) {
        String thumbnail = thumbnailUrl == null ? "null" : "\"" + thumbnailUrl + "\"";
        return """
                {"title":"%s","thumbnailUrl":%s,"scheduledAt":"%s"}
                """.formatted(title, thumbnail, scheduledAt);
    }

    @Test
    void 예약_개설하면_201과_SCHEDULED_상태를_반환한다() throws Exception {
        String body = scheduleRequestBody(
                "빈티지 데님 라이브", "https://cdn.example.com/live/1.jpg", LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.id").isNumber())
                .andExpect(jsonPath("$.data.status").value("SCHEDULED"))
                .andExpect(jsonPath("$.data.startedAt").doesNotExist())
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 방송_예정_시각이_과거면_400을_반환한다() throws Exception {
        String body = scheduleRequestBody("지난 라이브", null, LocalDateTime.now().minusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    void 방송명이_비어_있으면_400을_반환한다() throws Exception {
        String body = scheduleRequestBody("   ", null, LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .header("Authorization", "Bearer " + hostToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 미인증이면_401을_반환한다() throws Exception {
        String body = scheduleRequestBody("빈티지 데님 라이브", null, LocalDateTime.now().plusDays(1));

        mockMvc.perform(post("/api/lives/schedule")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isUnauthorized());
    }
}