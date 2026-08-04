package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.response.VideoTokenResponse;
import com.ssafy.backend.live.service.LiveVideoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "라이브 / 채팅(Lives)", description = "라이브 방송 개설/조회 API")
@RestController
@RequestMapping("/api/lives/{liveId}/video-token")
@RequiredArgsConstructor
public class LiveVideoController {

    private final LiveVideoService liveVideoService;

    @Operation(
            summary = "영상 접속 토큰 발급",
            description = "OpenVidu(LiveKit) 접속 토큰을 발급한다. **비회원도 발급받을 수 있다** — "
                    + "라이브 시청이 비회원 공개이기 때문이다.\n\n"
                    + "**역할은 서버가 정한다.** 호스트 본인이면 `PUBLISHER`(송출), 그 외에는 "
                    + "`VIEWER`(시청 전용)다. 클라이언트가 고를 수 없으므로 송출용·시청용 endpoint를 "
                    + "따로 두지 않았다.\n\n"
                    + "**진행 중(LIVE)인 방송에만 발급된다.** 예정 방송은 아직 room이 없고 종료된 방송은 "
                    + "정리됐다.\n\n"
                    + "토큰에는 만료가 있다(`expiresAt`). 방송이 그보다 길어지면 만료 전에 다시 호출해 "
                    + "재발급받으면 된다 — 재발급에 별도 제약은 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "진행 중인 방송이 아니거나 아직 room이 배정되지 않음(L013)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "503",
                    description = "영상 서버가 구성되지 않음(L012). 미디어 서버 구축 전에는 이 응답이 온다")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<VideoTokenResponse>> issueToken(
            Authentication authentication, @PathVariable Long liveId) {
        // 비회원은 authentication 자체가 없다 — 그것이 곧 시청 전용이라는 뜻이다.
        Long memberId = authentication == null ? null : (Long) authentication.getPrincipal();
        VideoTokenResponse response = liveVideoService.issueToken(memberId, liveId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
