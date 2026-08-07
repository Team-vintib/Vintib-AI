package com.ssafy.backend.global.client.dto;

/**
 * {@code POST /chat/moderate} 응답 — AI/app/chat/schemas.py의 {@code ModerateResponse}.
 * {@code action}은 {@code PASS|HIDE|BLOCK} 권고다. 실제 차단 집행은 BE가 한다.
 */
public record ModerateChatResponse(String verdict, String action, String reason) {

    public boolean isBlocked() {
        return "HIDE".equals(action) || "BLOCK".equals(action);
    }
}
