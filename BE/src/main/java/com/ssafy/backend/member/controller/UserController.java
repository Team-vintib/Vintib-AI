package com.ssafy.backend.member.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.request.LiveThumbnailUploadUrlRequest;
import com.ssafy.backend.live.dto.response.LiveThumbnailUploadUrlResponse;
import com.ssafy.backend.live.service.LiveThumbnailService;
import com.ssafy.backend.member.dto.request.MemberImageKeyRequest;
import com.ssafy.backend.member.dto.request.MemberImageUploadUrlRequest;
import com.ssafy.backend.member.dto.request.UpdateBioRequest;
import com.ssafy.backend.member.dto.request.UpdateInterestsRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberTypeRequest;
import com.ssafy.backend.member.dto.response.InterestsResponse;
import com.ssafy.backend.member.dto.response.MemberImageUploadUrlResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.dto.response.MypageSummaryResponse;
import com.ssafy.backend.member.dto.response.PublicProfileResponse;
import com.ssafy.backend.member.service.MemberImageService;
import com.ssafy.backend.member.service.UserService;
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
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
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
    private final MemberImageService memberImageService;
    private final LiveThumbnailService liveThumbnailService;

    @Operation(
            summary = "회원 기본 정보 조회",
            description = "본인의 기본 정보를 조회한다(MY-001). 사업자 인증 상태(businessVerificationStatus)도 함께 내려준다. "
                    + "본인 외 타인의 정보는 조회할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 조회 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> getProfile(
            Authentication authentication, @PathVariable Long id) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = userService.getProfile(requesterId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

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
            summary = "회원 유형 저장 및 온보딩 완료",
            description = """
                    회원 유형(GENERAL/BUSINESS)을 저장하고 온보딩을 최종 완료 처리한다(ONBOARD-004).
                    이미 온보딩을 완료한 회원이 다시 호출해도 유형을 갱신하며 성공 처리한다(멱등).
                    본인 외 타인의 정보를 수정할 수 없다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "저장 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "입력값 오류"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}/member-type")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> completeOnboarding(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody UpdateMemberTypeRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = userService.completeOnboarding(requesterId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "소개글 등록·수정",
            description = """
                    소개글을 저장한다(011 §5). 선택 입력이며, 부분 수정이 아니라 매번 전체를 새로
                    받는다(값을 안 보내면 지워진다). 커버 이미지는 이 엔드포인트가 아니라
                    `PUT /{id}/cover-image`(presigned 업로드 확정)로 관리한다. 본인 외 타인의
                    정보를 수정할 수 없다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "입력값 오류"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}/bio")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> updateBio(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody UpdateBioRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = userService.updateBio(requesterId, id, request);
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

    @Operation(
            summary = "마이페이지 요약 조회",
            description = """
                    마이페이지 첫 화면에 필요한 카운터(구매/판매/찜/팔로워/안읽은 알림)와 포인트 잔액을
                    한 번에 조회한다(에픽 S15P11A108-207 보너스). 본인 외 타인의 요약은 조회할 수 없다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 조회 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping("/{id}/mypage")
    public ResponseEntity<ApiResponse<MypageSummaryResponse>> getMypageSummary(
            Authentication authentication, @PathVariable Long id) {
        Long requesterId = (Long) authentication.getPrincipal();
        MypageSummaryResponse response = userService.getMypageSummary(requesterId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "공개 회원/판매자 프로필 조회",
            description = """
                    상품 상세 판매자, 검색 회원, 라이브 호스트의 공개 프로필을 조회한다(011 §3.3).
                    비회원도 조회할 수 있다. 로그인 상태로 조회하면 isFollowing이 조회자 기준으로
                    채워지고, 비회원이면 항상 false다. 전화번호 등 민감정보는 포함하지 않는다.
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @GetMapping("/{id}/profile")
    public ResponseEntity<ApiResponse<PublicProfileResponse>> getPublicProfile(
            Authentication authentication, @PathVariable Long id) {
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        PublicProfileResponse response = userService.getPublicProfile(viewerId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(summary = "프로필 이미지 업로드 URL 발급",
            description = "프로필 이미지를 S3에 직접 업로드할 수 있는 presigned URL을 발급한다(SY030). "
                    + "발급받은 key는 `PUT /{id}/profile-image`에 그대로 쓴다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 발급 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{id}/profile-image/upload-url")
    public ResponseEntity<ApiResponse<MemberImageUploadUrlResponse>> createProfileImageUploadUrl(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody MemberImageUploadUrlRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                memberImageService.createProfileImageUploadUrl(requesterId, id, request)));
    }

    @Operation(summary = "프로필 이미지 확정",
            description = "presigned 업로드가 끝난 key를 확정해 프로필 이미지로 저장한다(SY030). 본인 외 타인의 정보를 수정할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "저장 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "업로드가 확인되지 않은 key"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PutMapping("/{id}/profile-image")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> confirmProfileImage(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody MemberImageKeyRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = memberImageService.confirmProfileImage(requesterId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(summary = "프로필 이미지 삭제", description = "프로필 이미지를 지운다(SY030). 본인 외 타인의 정보를 수정할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/{id}/profile-image")
    public ResponseEntity<Void> deleteProfileImage(Authentication authentication, @PathVariable Long id) {
        Long requesterId = (Long) authentication.getPrincipal();
        memberImageService.deleteProfileImage(requesterId, id);
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "커버 이미지 업로드 URL 발급",
            description = "커버 이미지를 S3에 직접 업로드할 수 있는 presigned URL을 발급한다(SY030). "
                    + "발급받은 key는 `PUT /{id}/cover-image`에 그대로 쓴다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 발급 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{id}/cover-image/upload-url")
    public ResponseEntity<ApiResponse<MemberImageUploadUrlResponse>> createCoverImageUploadUrl(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody MemberImageUploadUrlRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                memberImageService.createCoverImageUploadUrl(requesterId, id, request)));
    }

    @Operation(summary = "커버 이미지 확정",
            description = "presigned 업로드가 끝난 key를 확정해 커버 이미지로 저장한다(SY030). 본인 외 타인의 정보를 수정할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "저장 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "업로드가 확인되지 않은 key"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PutMapping("/{id}/cover-image")
    public ResponseEntity<ApiResponse<MemberProfileResponse>> confirmCoverImage(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody MemberImageKeyRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        MemberProfileResponse response = memberImageService.confirmCoverImage(requesterId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(summary = "커버 이미지 삭제", description = "커버 이미지를 지운다(SY030). 본인 외 타인의 정보를 수정할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 수정 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/{id}/cover-image")
    public ResponseEntity<Void> deleteCoverImage(Authentication authentication, @PathVariable Long id) {
        Long requesterId = (Long) authentication.getPrincipal();
        memberImageService.deleteCoverImage(requesterId, id);
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "라이브 썸네일 업로드 URL 발급",
            description = "라이브 썸네일을 S3에 직접 업로드할 수 있는 presigned URL을 발급한다(FE 요청 021). "
                    + "라이브 생성 전이라 확정(confirm) 단계가 없다 — 응답의 `url`을 그대로 "
                    + "`POST /api/lives` 또는 `/api/lives/schedule`의 `thumbnailUrl`에 실어 보내면 된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 발급 불가"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "존재하지 않는 회원")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{id}/lives/thumbnail/upload-url")
    public ResponseEntity<ApiResponse<LiveThumbnailUploadUrlResponse>> createLiveThumbnailUploadUrl(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody LiveThumbnailUploadUrlRequest request) {
        Long requesterId = (Long) authentication.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                liveThumbnailService.createUploadUrl(requesterId, id, request)));
    }
}
