package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * {@code POST /chat/moderate} 응답 — AI/app/chat/schemas.py의 {@code ModerateResponse}.
 * {@code action}은 {@code PASS|HIDE|BLOCK} 권고다. 실제 차단 집행은 BE가 한다.
 *
 * <p>{@code muteRemainingSeconds}는 {@code verdict=TIMED_OUT}일 때만 채워진다(CH025) — 반복
 * 위반으로 그 방송에서 당분간 채팅 자체가 막힌 상태의 잔여 시간(초)이다.
 */
public record ModerateChatResponse(
        String verdict,
        String action,
        String reason,
        @JsonProperty("mute_remaining_seconds") Double muteRemainingSeconds) {

    public ModerateChatResponse(String verdict, String action, String reason) {
        this(verdict, action, reason, null);
    }

    public boolean isBlocked() {
        return "HIDE".equals(action) || "BLOCK".equals(action);
    }
}
