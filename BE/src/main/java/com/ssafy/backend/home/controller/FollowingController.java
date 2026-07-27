package com.ssafy.backend.home.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.service.FollowingService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "홈", description = "홈 화면 콘텐츠 조회 API")
@RestController
@RequestMapping("/api/home")
@RequiredArgsConstructor
public class FollowingController {

    private final FollowingService followingService;

    @Operation(summary = "팔로잉 콘텐츠 조회",
            description = "로그인한 회원이 팔로우한 회원들의 라이브·상품을 반환한다. 팔로우가 없거나 노출할 콘텐츠가 없으면 empty=true. "
                    + "(현재 Mock 응답 — 2주차에 팔로우·상품 도메인 실데이터로 교체 예정)")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @GetMapping("/following")
    public ResponseEntity<ApiResponse<FollowingContentResponse>> getFollowingContent(Authentication authentication) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(followingService.getFollowingContent(memberId)));
    }
}