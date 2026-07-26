package com.ssafy.backend.home.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.home.dto.response.HomeContentResponse;
import com.ssafy.backend.home.service.HomeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "홈", description = "홈 화면 콘텐츠 조회 API")
@RestController
@RequestMapping("/api/home")
@RequiredArgsConstructor
public class HomeController {

    private final HomeService homeService;

    @Operation(summary = "홈 콘텐츠 조회",
            description = "진행 중/예약 라이브와 상시 판매/경매 예정 상품을 섹션별로 반환한다. 비회원도 조회할 수 있다. "
                    + "(현재 Mock 응답 — 2주차에 상품 도메인 + 라이브 CRUD 실데이터로 교체 예정)")
    @ApiResponses(
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    )
    @GetMapping
    public ResponseEntity<ApiResponse<HomeContentResponse>> getHomeContent() {
        return ResponseEntity.ok(ApiResponse.success(homeService.getHomeContent()));
    }
}