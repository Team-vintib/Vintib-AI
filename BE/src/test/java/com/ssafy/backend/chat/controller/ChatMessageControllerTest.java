package com.ssafy.backend.chat.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.repository.ChatMessageRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
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
 * 채팅 과거 메시지 조회 테스트(-453, -454).
 *
 * <p>실제 시큐리티 필터 체인을 끼워 <b>비회원 200</b>을 검증한다. 라이브 시청이 비회원 공개이므로
 * 대화 읽기도 열려 있어야 한다.
 *
 * <p>{@code @AutoConfigureMockMvc}는 Spring Boot 4 모듈러 테스트에서 쓸 수 없어
 * {@code MockMvcBuilders.webAppContextSetup}으로 직접 구성한다(-294에서 확인).
 */
@SpringBootTest
class ChatMessageControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private FilterChainProxy springSecurityFilterChain;

    @Autowired
    private MemberRepository memberRepository;

    @Autowired
    private LiveRepository liveRepository;

    @Autowired
    private ChatMessageRepository chatMessageRepository;

    private MockMvc mockMvc;
    private Long liveId;
    private Member speaker;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(springSecurityFilterChain)
                .build();

        speaker = memberRepository.save(Member.builder()
                .email("chat-history-" + UUID.randomUUID() + "@example.com")
                .password("encoded")
                .name("시청자")
                .build());

        liveId = liveRepository.save(
                        Live.openNow(speaker, "빈티지 데님 라이브", null, LocalDateTime.now()))
                .getId();
    }

    /** 메시지 n건을 순서대로 저장하고 마지막(가장 최신) 메시지 ID를 돌려준다. */
    private Long 메시지_저장(int count) {
        Live live = liveRepository.findById(liveId).orElseThrow();
        Long lastId = null;
        for (int i = 1; i <= count; i++) {
            lastId = chatMessageRepository.save(
                            ChatMessage.userMessage(live, speaker, "메시지 " + i, LocalDateTime.now()))
                    .getId();
        }
        return lastId;
    }

    @Test
    void 비회원도_과거_메시지를_조회할_수_있다() throws Exception {
        메시지_저장(3);

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.content").isArray())
                .andExpect(jsonPath("$.data.content[0].content").value("메시지 3"))
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void 최신순으로_반환하고_다음_커서를_준다() throws Exception {
        메시지_저장(5);

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId).param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(2))
                .andExpect(jsonPath("$.data.content[0].content").value("메시지 5"))
                .andExpect(jsonPath("$.data.content[1].content").value("메시지 4"))
                .andExpect(jsonPath("$.data.hasNext").value(true))
                .andExpect(jsonPath("$.data.nextCursor").isNumber());
    }

    @Test
    void 커서를_주면_그보다_오래된_메시지만_나온다() throws Exception {
        메시지_저장(5);
        // 첫 페이지의 nextCursor 는 "메시지 4"의 ID 다. 그것을 커서로 넣으면 3, 2, 1 이 나와야 한다.
        String first = mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId).param("size", "2"))
                .andReturn().getResponse().getContentAsString();
        long cursor = Long.parseLong(first.replaceAll(".*\"nextCursor\":(\\d+).*", "$1"));

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("size", "2")
                        .param("cursor", String.valueOf(cursor)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content[0].content").value("메시지 3"))
                .andExpect(jsonPath("$.data.content[1].content").value("메시지 2"));
    }

    @Test
    void 마지막_페이지는_hasNext가_false이고_커서가_없다() throws Exception {
        메시지_저장(2);

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId).param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(2))
                .andExpect(jsonPath("$.data.hasNext").value(false))
                .andExpect(jsonPath("$.data.nextCursor").doesNotExist());
    }

    @Test
    void 메시지가_없으면_200과_빈_목록을_준다() throws Exception {
        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(0))
                .andExpect(jsonPath("$.data.hasNext").value(false));
    }

    @Test
    void 존재하지_않는_라이브면_404를_반환한다() throws Exception {
        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", 99_999_999L))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("L001"));
    }

    @Test
    void size가_허용_범위를_벗어나면_400을_반환한다() throws Exception {
        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId).param("size", "0"))
                .andExpect(status().isBadRequest());
    }

    /** 첫 페이지의 첫 메시지 ID를 꺼낸다. after 방향 검증의 기준점으로 쓴다. */
    private long 가장_오래된_메시지_ID() {
        return chatMessageRepository.findPageByLiveId(
                        liveId, null, org.springframework.data.domain.PageRequest.of(0, 100))
                .stream()
                .mapToLong(ChatMessage::getId)
                .min()
                .orElseThrow();
    }

    @Test
    void after를_주면_그보다_새로운_메시지를_오래된_순으로_준다() throws Exception {
        메시지_저장(5);
        long oldest = 가장_오래된_메시지_ID();

        // "메시지 1"(가장 오래된 것) 이후를 요청하면 2, 3 이 순서대로 와야 한다.
        // 최신순으로 자르면 5, 4 가 와서 끊긴 지점과 사이에 구멍이 생긴다 — 그것을 막는 것이 목적이다.
        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("after", String.valueOf(oldest))
                        .param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(2))
                .andExpect(jsonPath("$.data.content[0].content").value("메시지 2"))
                .andExpect(jsonPath("$.data.content[1].content").value("메시지 3"))
                .andExpect(jsonPath("$.data.hasNext").value(true));
    }

    @Test
    void after_방향도_nextCursor로_이어서_받을_수_있다() throws Exception {
        메시지_저장(5);
        long oldest = 가장_오래된_메시지_ID();

        String first = mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("after", String.valueOf(oldest))
                        .param("size", "2"))
                .andReturn().getResponse().getContentAsString();
        long next = Long.parseLong(first.replaceAll(".*\"nextCursor\":(\\d+).*", "$1"));

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("after", String.valueOf(next))
                        .param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content[0].content").value("메시지 4"))
                .andExpect(jsonPath("$.data.content[1].content").value("메시지 5"))
                .andExpect(jsonPath("$.data.hasNext").value(false));
    }

    @Test
    void 가장_최신_메시지_이후를_요청하면_빈_목록을_준다() throws Exception {
        메시지_저장(3);
        // 최신순 조회의 첫 건이 가장 새로운 메시지다.
        long latest = chatMessageRepository.findPageByLiveId(
                        liveId, null, org.springframework.data.domain.PageRequest.of(0, 1))
                .get(0)
                .getId();

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("after", String.valueOf(latest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.content.length()").value(0))
                .andExpect(jsonPath("$.data.hasNext").value(false));
    }

    @Test
    void cursor와_after를_동시에_주면_400을_반환한다() throws Exception {
        // 어느 방향을 의도한 것인지 알 수 없다. 임의로 하나를 고르면 FE 가 원인을 알 수 없다.
        메시지_저장(2);

        mockMvc.perform(get("/api/lives/{liveId}/chat-messages", liveId)
                        .param("cursor", "100")
                        .param("after", "1"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }
}