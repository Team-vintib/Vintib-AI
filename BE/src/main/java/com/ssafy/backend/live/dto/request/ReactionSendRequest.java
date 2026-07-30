package com.ssafy.backend.live.dto.request;

import com.ssafy.backend.live.entity.ReactionType;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * STOMP 반응 발행 payload. 목적지 {@code /app/lives/{liveId}/reactions}.
 *
 * <p>채팅 요청과 같은 이유로 Bean Validation 을 달지 않는다 — STOMP 는 MVC 검증 파이프라인을 타지
 * 않아 위반이 공통 에러 규격으로 전달되지 않는다. 검증은 서비스에서 {@code CustomException} 으로 한다.
 *
 * <p>{@code clientReactionId} 를 두지 않는다. 채팅은 낙관적으로 그린 말풍선을 실제 메시지로
 * 치환해야 해서 임시 ID 가 필요했지만, 반응은 <b>떠올랐다 사라지는 애니메이션</b>이라 치환할
 * 대상이 없다. 발행자가 자기 반응을 두 번 그리는 것은 브로드캐스트의 {@code senderId} 로 걸러낸다.
 */
public record ReactionSendRequest(

        @Schema(
                description = "반응 종류. 서버가 허용한 값만 받는다",
                example = "HEART",
                allowableValues = {"HEART", "FIRE", "CLAP", "WOW"})
        ReactionType type) {
}
