package com.ssafy.backend.chat.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * AI 판정(HIDE/BLOCK)으로 브로드캐스트가 생략된 메시지를 발신자 본인에게만 알린다
 * (-571 후속). 브로드캐스트가 없으면 발신자의 낙관적 렌더 말풍선이 "진짜 메시지로 치환"될
 * 신호를 영영 못 받아 화면에 그대로 남는다 — 이 알림으로 그 말풍선을 지우게 한다.
 */
public record ChatMessageBlockedNotice(

        @Schema(description = "차단된 메시지의 클라이언트 임시 ID", example = "tmp-3f9c1e")
        String clientMessageId) {
}
