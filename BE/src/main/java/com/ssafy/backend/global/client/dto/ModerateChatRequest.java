package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

/**
 * {@code POST /chat/moderate} 요청. 필드명은 AI 쪽 계약(AI/app/chat/schemas.py의
 * {@code ModerateRequest})을 그대로 따른다 — snake_case로 직렬화해야 한다.
 */
public record ModerateChatRequest(
        @JsonProperty("live_id") Long liveId,
        @JsonProperty("message_id") Long messageId,
        @JsonProperty("user_id") Long userId,
        String content,
        @JsonProperty("sent_at") LocalDateTime sentAt) {
}
