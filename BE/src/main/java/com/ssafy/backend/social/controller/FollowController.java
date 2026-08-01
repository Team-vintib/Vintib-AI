package com.ssafy.backend.social.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.social.dto.response.FollowResponse;
import com.ssafy.backend.social.service.FollowService;
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

// 경로는 APIs.md의 `/users/{id}/followers` 스펙을 그대로 따른다.
// 태그는 WishController가 이미 예약해둔 "팔로우 / 찜(Socials)"를 그대로 재사용한다.
@Tag(name = "팔로우 / 찜(Socials)", description = "팔로우, 상품 찜/해제 API")
@RestController
@RequestMapping("/api/users/{userId}")
@RequiredArgsConstructor
public class FollowController {

    private final FollowService followService;

    @Operation(summary = "팔로우",
            description = "대상 회원을 팔로우한다. 자기 자신은 팔로우할 수 없다. 이미 팔로우 중이면 에러 없이 "
                    + "현재 상태를 그대로 반환한다(멱등 — 팔로우 토글 버튼의 연타·중복 요청에도 안전).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "팔로우 상태(성공)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "자기 자신을 팔로우하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "대상 회원이 존재하지 않음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/followers")
    public ResponseEntity<ApiResponse<FollowResponse>> follow(Authentication authentication, @PathVariable Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(followService.follow(memberId, userId)));
    }

    @Operation(summary = "팔로우 해제",
            description = "대상 회원 팔로우를 해제한다. 팔로우 중이 아니었어도 에러 없이 204를 반환한다(멱등).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "해제 성공(이미 비팔로우 상태였어도 204)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/followers")
    public ResponseEntity<Void> unfollow(Authentication authentication, @PathVariable Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        followService.unfollow(memberId, userId);
        return ResponseEntity.noContent().build();
    }
}
