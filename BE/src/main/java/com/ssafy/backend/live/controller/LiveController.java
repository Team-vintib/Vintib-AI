package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.request.LiveStatusUpdateRequest;
import com.ssafy.backend.live.dto.response.LiveDetailResponse;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.service.LiveService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "라이브(Lives)", description = "라이브 방송 개설/조회 API")
@RestController
@RequestMapping("/api/lives")
@RequiredArgsConstructor
public class LiveController {

    private final LiveService liveService;

    @Operation(
            summary = "예약 라이브 개설",
            description = "방송 예정 시각을 지정해 라이브를 예약 개설한다. 생성 직후 상태는 SCHEDULED이며, "
                    + "방송 예정 시각은 반드시 미래여야 한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "개설 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패(방송명 누락, 예정 시각이 과거 등)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/schedule")
    public ResponseEntity<ApiResponse<LiveResponse>> scheduleLive(
            Authentication authentication, @Valid @RequestBody LiveScheduleRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.scheduleLive(hostId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "즉시 라이브 개설",
            description = "예약 없이 곧바로 방송을 시작한다. 생성 직후 상태는 LIVE이며, 시작 시각은 서버 시각으로 기록된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "개설 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패(방송명 누락 등)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<LiveResponse>> openLiveNow(
            Authentication authentication, @Valid @RequestBody LiveInstantRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.openLiveNow(hostId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "라이브 시청 정보 조회",
            description = "라이브 방 정보와 편성된 상품 목록을 함께 반환한다. **비회원도 조회할 수 있다.** "
                    + "영상 접속 토큰은 별도 발급 API가 담당한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @GetMapping("/{liveId}")
    public ResponseEntity<ApiResponse<LiveDetailResponse>> getLiveDetail(@PathVariable Long liveId) {
        LiveDetailResponse response = liveService.getLiveDetail(liveId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "방송 상태 전이",
            description = "방송 상태를 바꾼다. 허용되는 전이는 예정→진행(LIVE), 예정→취소(CANCELED), "
                    + "진행→종료(ENDED) 세 가지다. 종료·취소된 방송은 더 이상 전이되지 않는다. "
                    + "전이 시각은 서버 시각으로 기록된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "전이 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 허용되지 않는 전이"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @PatchMapping("/{liveId}/status")
    public ResponseEntity<ApiResponse<LiveResponse>> transitionStatus(
            Authentication authentication,
            @PathVariable Long liveId,
            @Valid @RequestBody LiveStatusUpdateRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveResponse response = liveService.transitionStatus(hostId, liveId, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}