package com.ssafy.backend.tryon.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUpdateRequest;
import com.ssafy.backend.tryon.dto.request.TryOnProfileUploadUrlRequest;
import com.ssafy.backend.tryon.dto.response.TryOnProfileResponse;
import com.ssafy.backend.tryon.dto.response.TryOnProfileUploadUrlResponse;
import com.ssafy.backend.tryon.service.TryOnProfileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 경로는 APIs.md의 `/users/{id}/tryon`(단수) 스펙을 따른다 — 시착 "결과" 목록인
// `/users/{userId}/tryons`(복수, TryOnController)와는 다른 리소스다.
// 사진 업로드는 상품 이미지와 동일한 presigned 2단계(ProductImageService 참고)를 쓴다.
@Tag(name = "AI 가상 시착(TryOns)", description = "온보딩·라이브 시착 패널에서 쓰는 전신 사진·신체 치수 프로필 API")
@RestController
@RequestMapping("/api/users/{userId}/tryon")
@RequiredArgsConstructor
public class TryOnProfileController {

    private final TryOnProfileService tryOnProfileService;

    @Operation(summary = "시착 프로필 사진 업로드 URL 발급",
            description = "전신 사진을 S3에 직접 업로드할 수 있는 presigned URL을 발급한다. 발급받은 key는 프로필 등록/수정 시 그대로 사용한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 프로필에 접근하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/upload-url")
    public ResponseEntity<ApiResponse<TryOnProfileUploadUrlResponse>> createUploadUrl(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody TryOnProfileUploadUrlRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(tryOnProfileService.createUploadUrl(userId, request)));
    }

    @Operation(summary = "시착 프로필 조회", description = "본인의 시착 프로필을 조회한다. 사진 URL은 짧은 만료시간의 presigned GET URL이다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 프로필을 조회하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "등록된 프로필이 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<TryOnProfileResponse>> getProfile(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(tryOnProfileService.getProfile(userId)));
    }

    @Operation(summary = "시착 프로필 등록/수정",
            description = "전신 사진 key와 신체 치수를 저장한다(최초 호출이면 등록, 이후 호출이면 수정을 겸하는 upsert). "
                    + "요청에 값을 보내지 않은 필드는 기존 값을 그대로 유지한다(부분 병합) — 온보딩과 라이브 시착 패널에서 나눠서 입력해도 된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "저장 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "업로드가 확인되지 않은 사진 key"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 프로필을 수정하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PutMapping
    public ResponseEntity<ApiResponse<TryOnProfileResponse>> upsertProfile(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody TryOnProfileUpdateRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(tryOnProfileService.upsertProfile(userId, request)));
    }

    @Operation(summary = "시착 프로필 삭제", description = "본인의 시착 프로필을 사진과 함께 S3·DB에서 삭제한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 프로필을 삭제하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "등록된 프로필이 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping
    public ResponseEntity<Void> deleteProfile(Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        tryOnProfileService.deleteProfile(userId);
        return ResponseEntity.noContent().build();
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.TRYON_PROFILE_NOT_OWNER);
        }
    }
}
