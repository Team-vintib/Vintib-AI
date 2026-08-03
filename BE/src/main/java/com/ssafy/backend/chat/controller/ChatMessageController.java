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

@Tag(name = "라이브 / 채팅(Lives)", description = "라이브 채팅 이력 조회 API. 실시간 송수신은 STOMP로 처리한다")
@Validated
@RestController
@RequestMapping("/api/lives/{liveId}/chat-messages")
@RequiredArgsConstructor
public class ChatMessageController {

    private final ChatMessageService chatMessageService;

    @Operation(
            summary = "채팅 과거 메시지 조회",
            description = "라이브의 대화 이력을 커서 페이징으로 반환한다. **비회원도 조회할 수 있다.** "
                    + "WebSocket은 접속 이후 메시지만 주므로 이력은 이 API로 채운다.\n\n"
                    + "**커서는 page 번호가 아니라 messageId다.** 채팅은 조회 중에도 계속 쌓여서 "
                    + "offset 방식이면 경계에서 메시지가 밀리거나 중복된다. 응답의 nextCursor를 "
                    + "다음 요청에 그대로 넣고, hasNext가 false면 더 없다는 뜻이다.\n\n"
                    + "**방향이 둘이다.**\n"
                    + "- `cursor` — 이 ID보다 **오래된** 메시지를 **최신순**으로. 위로 스크롤할 때 쓴다. "
                    + "생략하면 가장 최신부터\n"
                    + "- `after` — 이 ID보다 **새로운** 메시지를 **오래된 순**으로. 재접속 후 끊긴 구간을 "
                    + "메울 때 쓴다\n\n"
                    + "`after`의 정렬이 반대인 것은 의도다. 앞으로 채우는 조회를 최신순으로 자르면 "
                    + "'가장 새로운 30건'이 와서 끊긴 지점과 사이에 구멍이 남는다.\n\n"
                    + "두 파라미터를 동시에 주면 400이다. 차단 처리된 메시지는 응답에서 제외된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "범위를 벗어난 size 또는 cursor·after 동시 지정"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<CursorPageResponse<ChatMessageResponse>>> getMessages(
            @PathVariable Long liveId,
            @Parameter(description = "이 messageId보다 오래된 메시지를 최신순으로. 첫 페이지는 생략")
            @RequestParam(required = false) Long cursor,
            @Parameter(description = "이 messageId보다 새로운 메시지를 오래된 순으로. cursor와 함께 쓸 수 없다")
            @RequestParam(required = false) Long after,
            @RequestParam(defaultValue = "30") @Min(1) @Max(100) int size) {
        CursorPageResponse<ChatMessageResponse> response =
                chatMessageService.getMessages(liveId, cursor, after, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}