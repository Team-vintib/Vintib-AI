package com.ssafy.backend.global.websocket;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.converter.MessageConversionException;
import org.springframework.messaging.handler.annotation.MessageExceptionHandler;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.web.bind.annotation.ControllerAdvice;

/**
 * STOMP 공통 예외 처리. REST 의 {@code GlobalExceptionHandler}는 메시지 채널을 타지 않으므로
 * 실시간 계층에는 이쪽이 대응한다.
 *
 * <p><b>왜 컨트롤러마다 두지 않고 advice 로 모으는가.</b> {@code @MessageExceptionHandler}는
 * 컨트롤러 단위로 찾는다. 채팅·반응·경매마다 같은 핸들러를 복사해 두면 <b>새 STOMP 컨트롤러를
 * 추가할 때 빼먹은 곳만 조용히 무응답이 된다.</b> 발행자는 실패했다는 사실조차 못 받는다.
 *
 * <p>응답 본문은 REST 와 같은 {@link ApiResponse} 규격이다 — FE 가 에러 처리를 한 갈래로 유지한다.
 */
@Slf4j
@ControllerAdvice
public class StompExceptionAdvice {

    @MessageExceptionHandler(CustomException.class)
    @SendToUser("/queue/errors")
    public ApiResponse<?> handleCustomException(CustomException e) {
        log.warn("STOMP 처리 실패: {} - {}", e.getErrorCode().getCode(), e.getMessage());
        return ApiResponse.error(e.getErrorCode());
    }

    /**
     * payload 를 DTO 로 바꾸지 못했다.
     *
     * <p><b>이 예외는 핸들러 메서드가 실행되기 전에 터진다.</b> 그래서 서비스 안의 검증으로는
     * 잡을 수 없다 — 예를 들어 {@code ReactionType} enum 에 없는 값을 보내면 역직렬화 단계에서
     * 끝난다. 여기서 받지 않으면 발행자는 아무 응답도 받지 못하고 이유를 알 수 없다.
     */
    @MessageExceptionHandler(MessageConversionException.class)
    @SendToUser("/queue/errors")
    public ApiResponse<?> handleMessageConversionException(MessageConversionException e) {
        log.warn("STOMP payload 변환 실패: {}", e.getMessage());
        return ApiResponse.error(ErrorCode.INVALID_INPUT_VALUE);
    }
}
