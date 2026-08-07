package com.ssafy.backend.chat.service;

import com.ssafy.backend.global.client.AiClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;

/**
 * 판매자(호스트) 채팅을 반복질문 근거 문서로 seed한다(CH026). 실측치, 네고 가능 여부처럼
 * 상품 DB에 없는 정보를 판매자가 라이브 중 채팅으로 알려줄 때가 있는데, STT 파이프라인이
 * 아직 없어(CH024 문서 참고) 텍스트로 이미 들어오는 이 데이터라도 근거로 쌓는다.
 *
 * <p><b>별도 빈으로 분리한 이유</b> — {@code @Async}는 스프링 프록시를 거쳐야 비동기로
 * 동작하는데, {@link ChatMessageService} 안에서 자기 자신의 {@code @Async} 메서드를 호출하면
 * (self-invocation) 프록시를 안 거쳐 그냥 동기로 실행돼 버린다. 호스트 채팅은 메시지마다
 * (빈도 높음) 발생하므로, 이 호출이 동기로 AI를 때리면 호스트 본인 채팅 전송 체감 속도가
 * 느려진다 — 그래서 진짜로 비동기가 되도록 별도 빈으로 뺐다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class HostChatRagSeeder {

    private final AiClient aiClient;

    @Async
    public void seed(Long liveId, String content) {
        try {
            aiClient.seedChatRagDocument(liveId, content);
        } catch (RestClientException e) {
            log.warn("판매자 채팅 RAG seed 실패(liveId={}): {}", liveId, e.getMessage());
        }
    }
}
