package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.response.LiveReminderResponse;
import com.ssafy.backend.live.service.LiveReminderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 예약 라이브 시작 알림 신청/취소(FE 요청 008 §3.2.1).
 *
 * <p>{@link LiveController}와 경로 prefix가 달라 별도 컨트롤러로 분리한다.
 */
@Tag(name = "라이브(Lives)", description = "라이브 방송 개설/조회 API")
@RestController
@RequestMapping("/api/lives/{liveId}/reminders")
@RequiredArgsConstructor
public class LiveReminderController {

    private final LiveReminderService liveReminderService;

    @Operation(
            summary = "예약 라이브 시작 알림 신청",
            description = "이 방송이 시작할 때 알림을 받도록 신청한다. **예정(SCHEDULED) 상태에만 "
                    + "신청할 수 있다** — 이미 진행 중이면 바로 들어가면 되고, 종료·취소된 방송은 "
                    + "시작할 일이 없다.\n\n"
                    + "**같은 방송에 두 번 신청해도 200이다.** 결과 상태가 이미 원하는 대로이므로 "
                    + "에러로 만들지 않는다(중복 클릭 대응).\n\n"
                    + "알림은 **시작 10분 전** 또는 **호스트가 실제로 시작한 직후**(둘 중 먼저 오는 쪽) "
                    + "생성되며, `type=LIVE_REMINDER` · `refType=LIVE` · `refId={liveId}`로 알림함에 쌓인다. "
                    + "발송은 최대 1분 주기의 스케줄러가 처리하므로 정확한 초 단위 시각은 보장하지 않는다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "신청 성공(이미 신청돼 있어도 200)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "예정 상태가 아닌 방송(L007)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음(L001)")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<LiveReminderResponse>> register(
            Authentication authentication, @PathVariable Long liveId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(liveReminderService.register(memberId, liveId)));
    }

    @Operation(
            summary = "예약 라이브 시작 알림 취소",
            description = "알림 신청을 취소한다. **신청한 적이 없어도 200이다** — 결과 상태(신청 안 됨)가 "
                    + "이미 원하는 대로이기 때문이다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "취소 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping
    public ResponseEntity<ApiResponse<LiveReminderResponse>> cancel(
            Authentication authentication, @PathVariable Long liveId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(liveReminderService.cancel(memberId, liveId)));
    }
}
