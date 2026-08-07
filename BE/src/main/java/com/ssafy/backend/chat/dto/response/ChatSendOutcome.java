package com.ssafy.backend.chat.dto.response;

/**
 * {@code ChatMessageService.send()}의 결과. 정상 발행이면 {@code broadcastMessage}만,
 * AI가 HIDE/BLOCK/TIMED_OUT을 권고했으면 {@code blockedNotice}만 채워진다 — 컨트롤러는
 * {@link #isBlocked()}로 분기해 브로드캐스트할지 발신자에게만 알릴지 정한다.
 */
public record ChatSendOutcome(ChatMessageResponse broadcastMessage, ChatMessageBlockedNotice blockedNotice) {

    public static ChatSendOutcome broadcast(ChatMessageResponse message) {
        return new ChatSendOutcome(message, null);
    }

    public static ChatSendOutcome blocked(ChatMessageBlockedNotice notice) {
        return new ChatSendOutcome(null, notice);
    }

    public boolean isBlocked() {
        return broadcastMessage == null;
    }
}
