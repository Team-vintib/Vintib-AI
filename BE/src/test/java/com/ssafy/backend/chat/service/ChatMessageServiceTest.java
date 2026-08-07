package com.ssafy.backend.chat.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.dto.response.ChatSendOutcome;
import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.entity.SenderType;
import com.ssafy.backend.chat.repository.ChatMessageRepository;
import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.ChatAnswer;
import com.ssafy.backend.global.client.dto.ModerateChatResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;

/**
 * {@link ChatMessageService} 단위 테스트 — 특히 AI 동기 판정 배선(-571)을 중점적으로 본다.
 */
@ExtendWith(MockitoExtension.class)
class ChatMessageServiceTest {

    private static final Long LIVE_ID = 1L;
    private static final Long SENDER_ID = 2L;
    private static final LocalDateTime STARTED_AT = LocalDateTime.of(2026, 8, 7, 20, 0);

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private AiClient aiClient;

    private ChatMessageService chatMessageService;

    private Live live() {
        Member host = Member.builder().email("host@example.com").password("encoded").name("호스트").build();
        Live live = Live.openNow(host, "빈티지 데님 라이브", null, null, STARTED_AT);
        ReflectionTestUtils.setField(live, "id", LIVE_ID);
        return live;
    }

    private Member viewer() {
        Member member =
                Member.builder().email("viewer@example.com").password("encoded").name("시청자").build();
        ReflectionTestUtils.setField(member, "id", SENDER_ID);
        ReflectionTestUtils.setField(member, "nickname", "덕후");
        return member;
    }

    private void setUpChatMessageService() {
        chatMessageService =
                new ChatMessageService(chatMessageRepository, liveRepository, memberRepository, aiClient);
    }

    private void stubSaveReturnsArgumentWithId(Long messageId) {
        when(chatMessageRepository.save(any(ChatMessage.class))).thenAnswer(invocation -> {
            ChatMessage message = invocation.getArgument(0);
            ReflectionTestUtils.setField(message, "id", messageId);
            return message;
        });
    }

    @Test
    void PASS_판정이면_메시지가_정상적으로_반환된다() {
        setUpChatMessageService();
        Live live = live();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(memberRepository.findById(SENDER_ID)).thenReturn(Optional.of(viewer()));
        stubSaveReturnsArgumentWithId(10L);
        when(aiClient.moderateChatMessage(anyLong(), anyLong(), anyLong(), anyString(), any()))
                .thenReturn(new ModerateChatResponse("NORMAL", "PASS", "clean"));

        ChatSendOutcome result = chatMessageService.send(SENDER_ID, LIVE_ID, "사이즈 M 맞나요?", "tmp-1");

        assertThat(result.isBlocked()).isFalse();
        assertThat(result.broadcastMessage().content()).isEqualTo("사이즈 M 맞나요?");
    }

    @Test
    void BLOCK_판정이면_메시지는_저장되지만_반환되지_않는다() {
        setUpChatMessageService();
        Live live = live();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(memberRepository.findById(SENDER_ID)).thenReturn(Optional.of(viewer()));
        stubSaveReturnsArgumentWithId(11L);
        when(aiClient.moderateChatMessage(anyLong(), anyLong(), anyLong(), anyString(), any()))
                .thenReturn(new ModerateChatResponse("ABUSIVE", "BLOCK", "abuse:term"));

        ChatSendOutcome result = chatMessageService.send(SENDER_ID, LIVE_ID, "욕설성 발언", "tmp-2");

        assertThat(result.isBlocked()).isTrue();
        assertThat(result.blockedNotice().clientMessageId()).isEqualTo("tmp-2");
        assertThat(result.blockedNotice().muteRemainingSeconds()).isNull();
    }

    @Test
    void TIMED_OUT_판정이면_음소거_잔여시간과_함께_차단된다() {
        setUpChatMessageService();
        Live live = live();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(memberRepository.findById(SENDER_ID)).thenReturn(Optional.of(viewer()));
        stubSaveReturnsArgumentWithId(13L);
        when(aiClient.moderateChatMessage(anyLong(), anyLong(), anyLong(), anyString(), any()))
                .thenReturn(new ModerateChatResponse("TIMED_OUT", "BLOCK", "user_timed_out", 15.0));

        ChatSendOutcome result = chatMessageService.send(SENDER_ID, LIVE_ID, "아무 메시지", "tmp-mute");

        assertThat(result.isBlocked()).isTrue();
        assertThat(result.blockedNotice().muteRemainingSeconds()).isEqualTo(15.0);
    }

    @Test
    void AI_판정_호출이_실패해도_메시지는_통과한다() {
        setUpChatMessageService();
        Live live = live();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live));
        when(memberRepository.findById(SENDER_ID)).thenReturn(Optional.of(viewer()));
        stubSaveReturnsArgumentWithId(12L);
        when(aiClient.moderateChatMessage(anyLong(), anyLong(), anyLong(), anyString(), any()))
                .thenThrow(new RestClientException("connection refused"));

        ChatSendOutcome result = chatMessageService.send(SENDER_ID, LIVE_ID, "안녕하세요", "tmp-3");

        assertThat(result.isBlocked()).isFalse();
    }

    @Test
    void AI_메시지가_있으면_그_시각을_커서로_돌려준다() {
        setUpChatMessageService();
        LocalDateTime lastAiAt = STARTED_AT.plusMinutes(5);
        ChatMessage aiMessage = ChatMessage.aiMessage(live(), "답변", lastAiAt);
        when(chatMessageRepository.findTopByLive_IdAndSenderTypeOrderByCreatedAtDesc(LIVE_ID, SenderType.AI))
                .thenReturn(Optional.of(aiMessage));

        LocalDateTime cursor = chatMessageService.lastAiAnswerCursor(LIVE_ID);

        assertThat(cursor).isEqualTo(lastAiAt);
    }

    @Test
    void AI_메시지가_없으면_방송_시작_시각을_커서로_돌려준다() {
        setUpChatMessageService();
        when(chatMessageRepository.findTopByLive_IdAndSenderTypeOrderByCreatedAtDesc(LIVE_ID, SenderType.AI))
                .thenReturn(Optional.empty());
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live()));

        LocalDateTime cursor = chatMessageService.lastAiAnswerCursor(LIVE_ID);

        assertThat(cursor).isEqualTo(STARTED_AT);
    }

    @Test
    void 반복질문_답변들을_AI_메시지로_저장한다() {
        setUpChatMessageService();
        when(liveRepository.findById(LIVE_ID)).thenReturn(Optional.of(live()));
        stubSaveReturnsArgumentWithId(20L);
        LocalDateTime answeredAt = STARTED_AT.plusMinutes(3);
        List<ChatAnswer> answers = List.of(
                new ChatAnswer("ticket-1", "프리사이즈인가요?", "네, 프리사이즈입니다.", answeredAt));

        List<ChatMessageResponse> saved = chatMessageService.saveAiAnswers(LIVE_ID, answers);

        assertThat(saved).hasSize(1);
        assertThat(saved.get(0).content()).isEqualTo("네, 프리사이즈입니다.");
        assertThat(saved.get(0).senderType()).isEqualTo(SenderType.AI);
    }
}
