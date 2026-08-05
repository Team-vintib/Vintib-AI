package com.ssafy.backend.chat.dto.response;

import com.ssafy.backend.chat.entity.ChatMessage;
import com.ssafy.backend.chat.entity.SenderType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 채팅 메시지 한 건. <b>STOMP 브로드캐스트와 과거 조회 REST가 같은 형태를 쓴다</b> —
 * 두 경로가 다른 모양이면 FE가 어댑터를 두 개 만들어야 한다.
 */
public record ChatMessageResponse(

        @Schema(description = "메시지 ID. 재접속 후 누락분을 보충할 때 커서로 쓴다", example = "1044")
        Long messageId,

        @Schema(description = "작성자 회원 ID. 시스템·AI 메시지는 null", example = "31")
        Long senderId,

        @Schema(description = "작성자 표시명. 닉네임이 없으면 이름으로 대체된다", example = "빈티지장인")
        String senderNickname,

        @Schema(
                description = "작성자 프로필 이미지 URL. **현재 항상 null이다** — 회원 엔티티에 "
                        + "해당 필드가 아직 없다(서윤 담당 영역, 요청 문서 전달). 추가되면 채워진다")
        String senderProfileImageUrl,

        @Schema(description = "화자 구분", example = "USER", allowableValues = {"USER", "SYSTEM", "AI"})
        SenderType senderType,

        @Schema(description = "메시지 본문", example = "이 자켓 사이즈 M 맞나요?")
        String content,

        @Schema(description = "서버 수신 시각", example = "2026-07-30T14:02:11")
        LocalDateTime createdAt,

        @Schema(
                description = "발행 요청에 담긴 클라이언트 임시 ID를 그대로 되돌려준 값. 과거 조회에서는 null",
                example = "tmp-3f9c1e")
        String clientMessageId) {

    public static ChatMessageResponse from(ChatMessage message) {
        return of(message, null);
    }

    public static ChatMessageResponse of(ChatMessage message, String clientMessageId) {
        return new ChatMessageResponse(
                message.getId(),
                message.getSender() == null ? null : message.getSender().getId(),
                message.senderDisplayName(),
                // 회원 엔티티에 프로필 이미지 필드가 없다. 임의로 채우면 FE 가 실제 값으로 오해한다.
                null,
                message.getSenderType(),
                message.getContent(),
                message.getCreatedAt(),
                clientMessageId);
    }
}