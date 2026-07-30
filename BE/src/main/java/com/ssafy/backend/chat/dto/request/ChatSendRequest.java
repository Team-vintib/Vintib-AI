package com.ssafy.backend.chat.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * STOMP 채팅 발행 payload. 목적지 {@code /app/lives/{liveId}/chat}.
 *
 * <p><b>Bean Validation 애너테이션을 달지 않았다.</b> STOMP 메시지는 Spring MVC의 검증·예외
 * 처리 파이프라인을 타지 않아 {@code @Valid} 위반이 {@code GlobalExceptionHandler}로 오지
 * 않는다. 그래서 내용 검증은 서비스에서 명시적으로 하고 {@code CustomException}으로 통일한다 —
 * 그렇게 해야 실패 사유가 REST와 같은 에러 코드로 FE에 전달된다.
 */
public record ChatSendRequest(

        @Schema(description = "메시지 본문. 1~500자", example = "이 자켓 사이즈 M 맞나요?")
        String content,

        @Schema(
                description = "클라이언트가 만든 임시 ID. 응답에 그대로 되돌려주므로 낙관적 렌더 후 "
                        + "실제 메시지로 치환할 때 쓴다. 서버는 저장하지 않는다",
                example = "tmp-3f9c1e")
        String clientMessageId) {
}