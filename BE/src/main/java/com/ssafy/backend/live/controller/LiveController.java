package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
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
}