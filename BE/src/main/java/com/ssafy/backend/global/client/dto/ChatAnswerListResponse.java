package com.ssafy.backend.global.client.dto;

import java.util.List;

/** {@code GET /chat/lives/{live_id}/answers} 응답 — AI/app/chat/schemas.py의 {@code AnswerListResponse}. */
public record ChatAnswerListResponse(List<ChatAnswer> answers) {
}
