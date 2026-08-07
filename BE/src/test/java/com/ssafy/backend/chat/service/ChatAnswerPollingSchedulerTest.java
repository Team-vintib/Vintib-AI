package com.ssafy.backend.chat.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.entity.SenderType;
import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.ChatAnswer;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;

/**
 * {@link ChatAnswerPollingScheduler} 단위 테스트(-571) — 방송 단위 격리(하나 실패해도 나머지는
 * 계속 폴링됨)와 빈 답변일 때 브로드캐스트를 생략하는 것을 중점적으로 본다.
 */
@ExtendWith(MockitoExtension.class)
class ChatAnswerPollingSchedulerTest {

    private static final LocalDateTime STARTED_AT = LocalDateTime.of(2026, 8, 7, 20, 0);

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private ChatMessageService chatMessageService;

    @Mock
    private AiClient aiClient;

    @Mock
    private SimpMessagingTemplate messagingTemplate;

    private ChatAnswerPollingScheduler scheduler;

    private Live liveWithId(Long id) {
        Member host = Member.builder().email("host" + id + "@example.com").password("encoded").name("호스트").build();
        Live live = Live.openNow(host, "라이브 " + id, null, null, STARTED_AT);
        ReflectionTestUtils.setField(live, "id", id);
        return live;
    }

    private void setUpScheduler() {
        scheduler = new ChatAnswerPollingScheduler(liveRepository, chatMessageService, aiClient, messagingTemplate);
    }

    @Test
    void 새_답변이_있으면_저장하고_브로드캐스트한다() {
        setUpScheduler();
        Long liveId = 1L;
        when(liveRepository.findByStatusOrderByStartedAtDesc(eq(LiveStatus.LIVE), any(Pageable.class)))
                .thenReturn(List.of(liveWithId(liveId)));
        when(chatMessageService.lastAiAnswerCursor(liveId)).thenReturn(STARTED_AT);
        ChatAnswer answer = new ChatAnswer(
                "ticket-1",
                "프리사이즈인가요?",
                "네, 프리사이즈입니다.",
                STARTED_AT.plusMinutes(1).atZone(ZoneId.systemDefault()).toInstant());
        when(aiClient.getLiveAnswers(liveId, STARTED_AT)).thenReturn(List.of(answer));
        ChatMessageResponse response = new ChatMessageResponse(
                100L, null, null, null, SenderType.AI, "네, 프리사이즈입니다.", STARTED_AT.plusMinutes(1), null);
        when(chatMessageService.saveAiAnswers(liveId, List.of(answer))).thenReturn(List.of(response));

        scheduler.pollAnswers();

        verify(messagingTemplate).convertAndSend("/topic/lives/" + liveId + "/chat", response);
    }

    @Test
    void 새_답변이_없으면_브로드캐스트하지_않는다() {
        setUpScheduler();
        Long liveId = 1L;
        when(liveRepository.findByStatusOrderByStartedAtDesc(eq(LiveStatus.LIVE), any(Pageable.class)))
                .thenReturn(List.of(liveWithId(liveId)));
        when(chatMessageService.lastAiAnswerCursor(liveId)).thenReturn(STARTED_AT);
        when(aiClient.getLiveAnswers(liveId, STARTED_AT)).thenReturn(List.of());

        scheduler.pollAnswers();

        verify(chatMessageService, never()).saveAiAnswers(anyLong(), anyList());
        verify(messagingTemplate, never()).convertAndSend(anyString(), any(Object.class));
    }

    @Test
    void 한_방송이_실패해도_나머지_방송은_계속_폴링된다() {
        setUpScheduler();
        Long failingLiveId = 1L;
        Long healthyLiveId = 2L;
        when(liveRepository.findByStatusOrderByStartedAtDesc(eq(LiveStatus.LIVE), any(Pageable.class)))
                .thenReturn(List.of(liveWithId(failingLiveId), liveWithId(healthyLiveId)));
        when(chatMessageService.lastAiAnswerCursor(failingLiveId)).thenReturn(STARTED_AT);
        when(chatMessageService.lastAiAnswerCursor(healthyLiveId)).thenReturn(STARTED_AT);
        when(aiClient.getLiveAnswers(failingLiveId, STARTED_AT))
                .thenThrow(new RestClientException("connection refused"));
        when(aiClient.getLiveAnswers(healthyLiveId, STARTED_AT)).thenReturn(List.of());

        scheduler.pollAnswers();

        verify(aiClient, times(1)).getLiveAnswers(healthyLiveId, STARTED_AT);
    }
}
