package com.ssafy.backend.global.client.dto;

/**
 * {@code POST /chat/lives/{liveId}/documents} 요청 — STT 없이 반복질문 근거 문서를 채운다
 * (-571, CH024). BE가 상품 편성 시점에 호출한다.
 */
public record SeedChatDocumentRequest(String content) {
}
