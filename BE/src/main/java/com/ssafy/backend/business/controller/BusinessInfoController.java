package com.ssafy.backend.business.controller;

import com.ssafy.backend.business.dto.request.BusinessCertificateUploadUrlRequest;
import com.ssafy.backend.business.dto.request.BusinessInfoSubmitRequest;
import com.ssafy.backend.business.dto.response.BusinessCertificateUploadUrlResponse;
import com.ssafy.backend.business.dto.response.BusinessInfoResponse;
import com.ssafy.backend.business.service.BusinessInfoService;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 관리자 승인/거절, 정보 수정(MY-008)은 범위 밖 — 제출/조회/재제출까지만 다룬다.
// 사업자등록증 업로드는 상품 이미지·시착 프로필과 동일한 presigned 2단계를 쓴다.
@Tag(name = "사업자(Businesses)", description = "사업자 인증 정보 제출/조회, 세금계산서 발행/조회 API")
@RestController
@RequestMapping("/api/users/{userId}/business")
@RequiredArgsConstructor
public class BusinessInfoController {

    private final BusinessInfoService businessInfoService;

    @Operation(summary = "사업자등록증 업로드 URL 발급",
            description = "사업자등록증 이미지를 S3에 직접 업로드할 수 있는 presigned URL을 발급한다. 발급받은 key는 제출 시 그대로 사용한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자로 접근하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/upload-url")
    public ResponseEntity<ApiResponse<BusinessCertificateUploadUrlResponse>> createUploadUrl(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody BusinessCertificateUploadUrlRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(businessInfoService.createUploadUrl(userId, request)));
    }

    @Operation(summary = "사업자 정보 제출/재제출",
            description = "사업자 정보를 제출한다(최초 제출은 PENDING 생성, REJECTED 상태에서는 재제출로 동작). "
                    + "PENDING·APPROVED 상태에서 다시 호출하면 409로 거부된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "제출 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "업로드가 확인되지 않은 인증서 key"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자로 접근하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 제출했거나 승인된 사업자 정보")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<BusinessInfoResponse>> submit(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody BusinessInfoSubmitRequest request) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(businessInfoService.submit(userId, request)));
    }

    @Operation(summary = "사업자 정보 조회",
            description = "본인의 사업자 인증 상태를 조회한다. 제출 이력이 없으면 status=NONE으로 200 응답한다(에러 아님).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자로 접근하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<BusinessInfoResponse>> getStatus(
            Authentication authentication, @PathVariable Long userId) {
        requireSelf(authentication, userId);
        return ResponseEntity.ok(ApiResponse.success(businessInfoService.getStatus(userId)));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.BUSINESS_INFO_FORBIDDEN);
        }
    }
}
