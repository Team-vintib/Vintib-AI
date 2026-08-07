package com.ssafy.backend.chat.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * AI 판정(HIDE/BLOCK/TIMED_OUT)으로 브로드캐스트가 생략된 메시지를 발신자 본인에게만 알린다
 * (-571 후속). 브로드캐스트가 없으면 발신자의 낙관적 렌더 말풍선이 "진짜 메시지로 치환"될
 * 신호를 영영 못 받아 화면에 그대로 남는다 — 이 알림으로 그 말풍선을 지우게 한다.
 *
 * <p>{@code muteRemainingSeconds}는 반복 위반으로 임시 음소거된 경우에만 채워진다(CH025).
 * 단순 차단(욕설·도배 메시지 1건)은 {@code null}이다 — FE가 이 값의 유무로 "메시지 하나만
 * 막힘"과 "당분간 채팅 자체가 막힘"을 구분한다.
 */
public record ChatMessageBlockedNotice(

        @Schema(description = "차단된 메시지의 클라이언트 임시 ID", example = "tmp-3f9c1e")
        String clientMessageId,

        @Schema(description = "임시 음소거 잔여 시간(초). 단순 메시지 차단이면 null", example = "15.0")
        Double muteRemainingSeconds) {

    public static ChatMessageBlockedNotice blocked(String clientMessageId) {
        return new ChatMessageBlockedNotice(clientMessageId, null);
    }

    public static ChatMessageBlockedNotice muted(String clientMessageId, double muteRemainingSeconds) {
        return new ChatMessageBlockedNotice(clientMessageId, muteRemainingSeconds);
    }
}
