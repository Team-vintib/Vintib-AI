package com.ssafy.backend.home.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.home.dto.response.HomeContentResponse;
import com.ssafy.backend.home.service.HomeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "홈(Home)", description = "홈 화면 콘텐츠 조회 API")
@RestController
@RequestMapping("/api/home")
@RequiredArgsConstructor
public class HomeController {

    private final HomeService homeService;

    @Operation(summary = "홈 콘텐츠 조회",
            description = "진행 중/예약 라이브, 상시 판매/경매 예정 상품, 카테고리별 상품 탭을 섹션별로 반환한다. "
                    + "**비회원도 조회할 수 있다.** 다만 토큰을 함께 보내면 상품 카드의 `isWished`가 채워지고, "
                    + "비회원 요청이면 `isWished`는 null로 내려간다. 모든 섹션은 빈 배열일 수 있다. "
                    + "(현재 Mock 응답 — 상품 도메인 + 라이브 조회 질의가 준비되면 실데이터로 교체 예정)")
    @ApiResponses(
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    )
    @GetMapping
    public ResponseEntity<ApiResponse<HomeContentResponse>> getHomeContent(Authentication authentication) {
        // 공개 API라 인증이 없을 수 있다. 있으면 회원별 상태(찜 여부)를 채워 내린다.
        Long memberId = authentication != null ? (Long) authentication.getPrincipal() : null;
        return ResponseEntity.ok(ApiResponse.success(homeService.getHomeContent(memberId)));
    }
}