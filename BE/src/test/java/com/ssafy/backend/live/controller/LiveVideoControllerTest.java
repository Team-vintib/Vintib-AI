package com.ssafy.backend.live.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.live.service.LiveVideoService;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
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
 * 영상 접속 토큰 발급 테스트(-449).
 *
 * <p><b>OpenVidu 설정을 테스트 속성으로 주입한다.</b> 실제 기본값은 비어 있어(서버 미구축)
 * 그대로 두면 전부 503이 된다. 여기서 채우는 값은 <b>서명에만 쓰이고 서버로 나가지 않는다</b> —
 * 토큰이 로컬 서명이라 가능한 방식이다.
 */
@SpringBootTest(properties = {
        "openvidu.server-url=wss://openvidu.test.local",
        "openvidu.api-key=devkey",
        "openvidu.api-secret=secret-that-is-long-enough-for-hmac-sha256",
        "openvidu.token-ttl=2h"
})
class LiveVideoControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    private MockMvc mockMvc;
    private Member host;
    private String hostToken;
    private String viewerToken;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        host = saveMember("호스트");
        Member viewer = saveMember("시청자");
        hostToken = jwtTokenProvider.createAccessToken(host.getId(), host.getEmail());
        viewerToken = jwtTokenProvider.createAccessToken(viewer.getId(), viewer.getEmail());
    }

    private Member saveMember(String name) {
        Member member = Member.builder()
                .email("video-" + name + "-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name(name)
                .build();
        // SY019 게이트: 온보딩 미완료 회원은 이 컨트롤러 자체를 못 쓰므로 완료 상태로 만든다.
        // 닉네임은 unique 제약이 있어 매 호출마다 겹치지 않게 만든다.
        String nickname = name + "-" + UUID.randomUUID().toString().substring(0, 8);
        member.updateBasicInfo(nickname, "01000000000", "서울", "1층", null, com.ssafy.backend.member.entity.Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        return memberRepository.save(member);
    }

    /** room 이 배정된 진행 중 방송. 실제 개설 경로와 같은 방식으로 이름을 넣는다. */
    private Long 진행_중인_방송() {
        Live live = liveRepository.save(Live.openNow(host, "빈티지 데님 라이브", null, LocalDateTime.now()));
        live.assignOpenviduRoom(LiveVideoService.newRoomName(live.getId()));
        return liveRepository.save(live).getId();
    }

    @Test
    void 호스트에게는_송출_토큰이_발급된다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/video-token", 진행_중인_방송())
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("PUBLISHER"))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.roomName").isNotEmpty())
                .andExpect(jsonPath("$.data.serverUrl").value("wss://openvidu.test.local"))
                .andExpect(jsonPath("$.data.expiresAt").isNotEmpty());
    }

    @Test
    void 다른_회원에게는_시청_토큰이_발급된다() throws Exception {
        // 역할은 서버가 정한다 — 호스트가 아니면 요청 방식과 무관하게 VIEWER 다.
        mockMvc.perform(post("/api/lives/{liveId}/video-token", 진행_중인_방송())
                        .header("Authorization", "Bearer " + viewerToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("VIEWER"));
    }

    @Test
    void 비회원도_시청_토큰을_받는다() throws Exception {
        // 라이브 시청이 비회원 공개라 영상도 열려 있어야 한다.
        mockMvc.perform(post("/api/lives/{liveId}/video-token", 진행_중인_방송()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("VIEWER"))
                .andExpect(jsonPath("$.data.token").isNotEmpty());
    }

    @Test
    void 아직_시작되지_않은_방송에는_토큰을_발급하지_않는다() throws Exception {
        Long scheduled = liveRepository.save(
                        Live.schedule(host, "예약 방송", null, LocalDateTime.now().plusDays(1)))
                .getId();

        // 예정 방송은 room 자체가 없다.
        mockMvc.perform(post("/api/lives/{liveId}/video-token", scheduled)
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("L013"));
    }

    @Test
    void 종료된_방송에는_토큰을_발급하지_않는다() throws Exception {
        Live live = liveRepository.findById(진행_중인_방송()).orElseThrow();
        live.transitionTo(LiveStatus.ENDED, LocalDateTime.now());
        liveRepository.save(live);

        mockMvc.perform(post("/api/lives/{liveId}/video-token", live.getId())
                        .header("Authorization", "Bearer " + hostToken))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("L013"));
    }

    @Test
    void 존재하지_않는_라이브는_404를_반환한다() throws Exception {
        mockMvc.perform(post("/api/lives/{liveId}/video-token", 999_999L))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L001"));
    }
}
