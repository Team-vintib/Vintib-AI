package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

/**
 * 반복질문 자동답변 한 건 — AI/app/chat/schemas.py의 {@code FaqAnswer}. 근거 없는(ungrounded)
 * 답변은 애초에 목록에 안 실려 오므로 BE가 따로 걸러낼 필요는 없다(036 요청 문서).
 */
public record ChatAnswer(
        String ticket,
        String question,
        String answer,
        @JsonProperty("created_at") LocalDateTime createdAt) {
}
