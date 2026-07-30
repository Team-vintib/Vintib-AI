package com.ssafy.backend.chat.controller;

import com.ssafy.backend.chat.dto.response.ChatMessageResponse;
import com.ssafy.backend.chat.service.ChatMessageService;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.CursorPageResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "라이브 채팅(Chat)", description = "라이브 채팅 이력 조회 API. 실시간 송수신은 STOMP로 처리한다")
@Validated
@RestController
@RequestMapping("/api/lives/{liveId}/chat-messages")
@RequiredArgsConstructor
public class ChatMessageController {

    private final ChatMessageService chatMessageService;

    @Operation(
            summary = "채팅 과거 메시지 조회",
            description = "라이브의 지난 대화를 최신순 커서 페이징으로 반환한다. **비회원도 조회할 수 있다.** "
                    + "WebSocket은 접속 이후 메시지만 주므로 중간에 입장한 시청자는 이 API로 이력을 채운다. "
                    + "재접속 후 누락분을 보충할 때도 마지막으로 받은 messageId를 cursor로 넣으면 된다.\n\n"
                    + "**커서는 page 번호가 아니라 messageId다.** 채팅은 조회 중에도 계속 쌓여서 "
                    + "offset 방식이면 경계에서 메시지가 밀리거나 중복된다. 응답의 nextCursor를 "
                    + "다음 요청에 그대로 넣고, hasNext가 false면 더 없다는 뜻이다.\n\n"
                    + "차단 처리된 메시지는 응답에서 제외된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "범위를 벗어난 size"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<CursorPageResponse<ChatMessageResponse>>> getMessages(
            @PathVariable Long liveId,
            @Parameter(description = "이 messageId보다 오래된 메시지를 가져온다. 첫 페이지는 생략")
            @RequestParam(required = false) Long cursor,
            @RequestParam(defaultValue = "30") @Min(1) @Max(100) int size) {
        CursorPageResponse<ChatMessageResponse> response =
                chatMessageService.getMessages(liveId, cursor, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}