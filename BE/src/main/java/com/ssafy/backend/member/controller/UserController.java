package com.ssafy.backend.member.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 회원 도메인 REST 컨트롤러.
 * 현재 구현 범위: 기본 정보 수정(ONBOARD-001, MY-001).
 */
@Tag(name = "회원(Users)", description = "회원 정보 조회·수정 API")
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @Operation(
            summary = "회원 기본 정보 등록·수정",
            description = """
                    닉네임·전화번호·주소·성별을 저장한다.
                    온보딩 첫 완료 시(ONBOARD-001)와 마이페이지 수정 시(MY-001) 동일 엔드포인트를 사용한다.
                    본인 외 타인의 정보를 수정할 수 없다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "입력값 오류"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "닉네임 중복")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> updateBasicInfo(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody UpdateMemberRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = userService.updateBasicInfo(requesterId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
