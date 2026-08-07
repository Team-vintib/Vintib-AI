package com.ssafy.backend.chat.service;

import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.client.dto.ChatAnswer;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Pageable;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;

/**
 * 반복질문 자동답변 폴링(CHAT-002, -571). AI 게이트웨이는 BE 공개 API 없이 CHAT-001
 * 파이프라인에 얹는 설계라(`docs/requests/BE/036-chat-rag-answer-public-api.md`), BE가
 * 직접 {@code GET /chat/lives/{id}/answers}를 주기적으로 물어봐서 새 답변을 채팅
 * 메시지로 편입시킨다 — 사용자 요청으로 트리거되는 지연 폴링이 안 통하는 자리라(채팅은
 * 계속 흘러가지 조회 시점이 따로 없다) 여기만 스케줄러를 쓴다.
 *
 * <p>{@link com.ssafy.backend.live.service.LiveAutoStartScheduler}와 같은 이유로
 * {@code fixedDelay}를 쓴다 — 한 번이 늦어져도 다음 실행이 겹쳐 들어오지 않는다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatAnswerPollingScheduler {

    private static final long INTERVAL_MS = 5_000;

    private final LiveRepository liveRepository;
    private final ChatMessageService chatMessageService;
    private final AiClient aiClient;
    private final SimpMessagingTemplate messagingTemplate;

    @Scheduled(fixedDelay = INTERVAL_MS, initialDelay = INTERVAL_MS)
    public void pollAnswers() {
        List<Live> liveBroadcasts =
                liveRepository.findByStatusOrderByStartedAtDesc(LiveStatus.LIVE, Pageable.unpaged());

        for (Live live : liveBroadcasts) {
            try {
                pollAnswersFor(live.getId());
            } catch (Exception e) {
                // 방송 하나가 실패해도 나머지 방송 폴링은 계속돼야 한다. 다음 주기에 재시도된다.
                log.warn("반복질문 답변 폴링 실패(liveId={}): {}", live.getId(), e.getMessage());
            }
        }
    }

    private void pollAnswersFor(Long liveId) {
        LocalDateTime since = chatMessageService.lastAiAnswerCursor(liveId);

        List<ChatAnswer> answers;
        try {
            answers = aiClient.getLiveAnswers(liveId, since);
        } catch (RestClientException e) {
            log.warn("AI 게이트웨이 답변 조회 실패(liveId={}): {}", liveId, e.getMessage());
            return;
        }
        if (answers.isEmpty()) {
            return;
        }

        List<ChatMessageResponse> saved = chatMessageService.saveAiAnswers(liveId, answers);
        for (ChatMessageResponse response : saved) {
            messagingTemplate.convertAndSend("/topic/lives/" + liveId + "/chat", response);
        }
    }
}
