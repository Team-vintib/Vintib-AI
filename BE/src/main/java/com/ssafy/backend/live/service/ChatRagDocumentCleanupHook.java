package com.ssafy.backend.live.service;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.live.entity.Live;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import org.springframework.web.client.RestClientException;

/**
 * 방송이 끝나면 반복질문 근거 문서(chat_rag_document)를 지운다(CH026 후속).
 *
 * <p>종료된 방송은 더 이상 채팅을 못 쳐서({@code INVALID_LIVE_STATE}) 반복질문 자체가 다시
 * 트리거될 일이 없다 — seed 문서가 그 시점부터 영구히 안 쓰인다(사용자 확인).
 *
 * <p>{@link OpenViduRoomCleanupHook}과 같은 이유로 커밋 후로 미룬다 — 훅 안에서 곧바로 HTTP
 * 호출을 하면 네트워크가 끝날 때까지 DB 커넥션을 쥐게 되고, AI 게이트웨이가 느리면 방송
 * 종료 자체가 그만큼 느려지거나 실패한다. 실패해도(AI 장애 등) 방송 종료는 막지 않는다 —
 * 문서가 안 지워지는 것보다 종료가 안 되는 쪽이 훨씬 나쁘다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatRagDocumentCleanupHook implements LiveCleanupHook {

    private final ApplicationEventPublisher eventPublisher;
    private final AiClient aiClient;

    /** 트랜잭션 안. 여기서는 발행만 한다. */
    @Override
    public void onLiveEnded(Live live) {
        eventPublisher.publishEvent(new ChatRagDocumentsCleared(live.getId()));
    }

    /** 커밋 후. 실패해도 로그만 남기고 넘어간다. */
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void deleteDocumentsAfterCommit(ChatRagDocumentsCleared event) {
        try {
            aiClient.deleteChatRagDocuments(event.liveId());
        } catch (RestClientException e) {
            log.warn("반복질문 근거 문서 정리 실패(liveId={}): {}", event.liveId(), e.getMessage());
        }
    }

    record ChatRagDocumentsCleared(Long liveId) {
    }
}
