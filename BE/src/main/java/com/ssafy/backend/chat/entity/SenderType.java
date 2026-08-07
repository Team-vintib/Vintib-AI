package com.ssafy.backend.chat.entity;

/**
 * 채팅 메시지 화자. DB 제약 {@code ck_chat_sender_type}와 값이 일치해야 한다.
 */
public enum SenderType {

    /** 로그인 회원 발언(CHAT-001). 비회원은 시청만 가능하다. */
    USER,

    /** 입장·퇴장·경매 안내 등 서버가 만든 메시지. 작성자가 없다. */
    SYSTEM,

    /** AI 자동 답변(CHAT-002, 반복질문 자동답변). */
    AI
}