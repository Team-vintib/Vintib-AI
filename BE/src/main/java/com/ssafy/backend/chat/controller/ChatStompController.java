package com.ssafy.backend.chat.controller;

import com.ssafy.backend.chat.dto.request.ChatSendRequest;
import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.service.ChatMessageService;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.websocket.StompPrincipal;
import java.security.Principal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageExceptionHandler;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.stereotype.Controller;

/**
 * 실시간 채팅 송수신(CHAT-001).
 *
 * <p>발행 {@code /app/lives/{liveId}/chat} → 구독 {@code /topic/lives/{liveId}/chat}.
 *
 * <p><b>ack를 위한 별도 목적지를 두지 않는다.</b> 브로드캐스트에 발행자의
 * {@code clientMessageId}를 그대로 실어 보내면, 발행자는 자기 값이 돌아온 것을 보고 낙관적으로
 * 그려둔 말풍선을 실제 메시지로 치환하고 나머지 구독자는 그 필드를 무시한다. 목적지를 하나로
 * 유지하는 편이 ack 채널을 따로 만들어 순서를 맞추는 것보다 단순하다 — 클라이언트가 만든
 * 임시 문자열이라 노출돼도 문제가 없다.
 *
 * <p>실패는 {@code /user/queue/errors}로 발행자에게만 보낸다. 브로드캐스트 토픽에 실어 보내면
 * 남의 실패 메시지가 모든 시청자 화면에 뜬다.
 */
@Slf4j
@Controller
@RequiredArgsConstructor
public class ChatStompController {

    private final ChatMessageService chatMessageService;
    private final SimpMessagingTemplate messagingTemplate;

    @MessageMapping("/lives/{liveId}/chat")
    public void sendMessage(
            @DestinationVariable Long liveId,
            @Payload ChatSendRequest request,
            Principal principal) {
        Long senderId = memberIdOf(principal);

        ChatMessageResponse response =
                chatMessageService.send(senderId, liveId, request.content(), request.clientMessageId());

        // 저장이 커밋된 뒤에 나간다 — send()의 트랜잭션이 이 시점에 이미 끝나 있다.
        // 커밋 전에 쏘면 롤백 시 유령 메시지가 모든 시청자 화면에 남는다.
        messagingTemplate.convertAndSend("/topic/lives/" + liveId + "/chat", response);
    }

    /**
     * STOMP 예외 처리. REST 의 {@code GlobalExceptionHandler}는 메시지 채널을 타지 않으므로
     * 여기서 따로 잡아야 한다. 응답 본문은 REST 와 같은 {@link ApiResponse} 규격을 쓴다 —
     * FE 가 에러 처리를 한 갈래로 유지할 수 있다.
     */
    @MessageExceptionHandler(CustomException.class)
    @SendToUser("/queue/errors")
    public ApiResponse<?> handleCustomException(CustomException e) {
        log.warn("STOMP CustomException: {} - {}", e.getErrorCode().getCode(), e.getMessage());
        return ApiResponse.error(e.getErrorCode());
    }

    /** 토큰 없이 붙은 세션은 principal 이 없다 — 그것이 곧 비회원이다. */
    private Long memberIdOf(Principal principal) {
        return principal instanceof StompPrincipal stompPrincipal ? stompPrincipal.memberId() : null;
    }
}