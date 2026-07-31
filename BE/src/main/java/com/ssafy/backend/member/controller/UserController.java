package com.ssafy.backend.member.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.member.dto.request.UpdateInterestsRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.response.InterestsResponse;
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
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
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
                    닉네임·전화번호·주소·상세주소·성별을 저장한다(우편번호는 선택).
                    온보딩 첫 완료 시(ONBOARD-001)와 마이페이지 수정 시(MY-001) 동일 엔드포인트를 사용하며,
                    우편번호를 제외한 모든 필드가 매번 필수다(부분 수정이 아니다).
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

    @Operation(
            summary = "관심 브랜드·카테고리 조회",
            description = "회원이 등록한 관심 브랜드·카테고리 목록을 조회한다. 본인 외 타인의 정보는 조회할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 조회 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{id}/interests")
    public ResponseEntity<ApiResponse<InterestsResponse>> getInterests(
            Authentication authentication,
            @PathVariable Long id) {
        Long requesterId = (Long) authentication.getPrincipal();
        InterestsResponse response = userService.getInterests(requesterId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "관심 브랜드·카테고리 등록·수정",
            description = """
                    관심 브랜드·카테고리 목록을 전체 교체한다(부분 추가/삭제가 아니다).
                    온보딩 첫 완료 시(ONBOARD-002)와 마이페이지 수정 시(MY-001) 동일 엔드포인트를 사용하며,
                    선택 입력이라 빈 배열(건너뛰기)도 허용한다. 본인 외 타인의 정보를 수정할 수 없다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "존재하지 않는 브랜드/카테고리 ID 포함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PutMapping("/{id}/interests")
    public ResponseEntity<ApiResponse<InterestsResponse>> updateInterests(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody UpdateInterestsRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        InterestsResponse response = userService.updateInterests(requesterId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
