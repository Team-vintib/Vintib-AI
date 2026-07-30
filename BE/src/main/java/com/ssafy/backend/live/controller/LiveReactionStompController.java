package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.websocket.StompPrincipal;
import com.ssafy.backend.live.dto.request.ReactionSendRequest;
import com.ssafy.backend.live.dto.response.ReactionResponse;
import com.ssafy.backend.live.service.LiveReactionService;
import java.security.Principal;
import lombok.RequiredArgsConstructor;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

/**
 * 반응 이모지 송수신.
 *
 * <p>발행 {@code /app/lives/{liveId}/reactions} → 구독 {@code /topic/lives/{liveId}/reactions}.
 *
 * <p><b>채팅과 달리 커밋 시점을 신경 쓰지 않는다.</b> 저장하는 것이 없어 롤백될 트랜잭션도 없고,
 * 따라서 "유령 반응"이 생길 수 없다. 검증만 통과하면 곧바로 중계한다.
 *
 * <p>실패는 {@link com.ssafy.backend.global.websocket.StompExceptionAdvice}가
 * {@code /user/queue/errors} 로 발행자에게만 보낸다 — rate limit 에 걸린 사실이 모든 시청자에게
 * 보일 이유가 없다.
 */
@Controller
@RequiredArgsConstructor
public class LiveReactionStompController {

    private final LiveReactionService liveReactionService;
    private final SimpMessagingTemplate messagingTemplate;

    @MessageMapping("/lives/{liveId}/reactions")
    public void sendReaction(
            @DestinationVariable Long liveId,
            @Payload ReactionSendRequest request,
            Principal principal) {
        ReactionResponse response =
                liveReactionService.react(memberIdOf(principal), liveId, request.type());

        messagingTemplate.convertAndSend("/topic/lives/" + liveId + "/reactions", response);
    }

    /** 토큰 없이 붙은 세션은 principal 이 없다 — 그것이 곧 비회원이다. */
    private Long memberIdOf(Principal principal) {
        return principal instanceof StompPrincipal stompPrincipal ? stompPrincipal.memberId() : null;
    }
}
