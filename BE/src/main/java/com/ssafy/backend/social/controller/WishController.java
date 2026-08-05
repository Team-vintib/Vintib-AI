package com.ssafy.backend.social.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.social.dto.request.WishCreateRequest;
import com.ssafy.backend.social.dto.response.WishItemResponse;
import com.ssafy.backend.social.dto.response.WishResponse;
import com.ssafy.backend.social.service.WishService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

// 경로는 APIs.md의 `/users/{id}/wishes`, `/users/{userId}/wishes/{id}` 스펙을 그대로 따른다.
// {id}는 별도 찜 PK가 없어(복합키) 상품 ID를 그대로 받는다 — TryOnController와 동일한 표기 관례.
// 태그는 APIs.md "팔로우 / 찜 (Socials)" 섹션 기준 — 이후 FollowController가 생기면 같은 태그명을 써서 Swagger에서 묶인다.
@Tag(name = "팔로우 / 찜(Socials)", description = "팔로우, 상품 찜/해제 API")
@RestController
@RequestMapping("/api/users/{userId}/wishes")
@RequiredArgsConstructor
public class WishController {

    private final WishService wishService;

    @Operation(summary = "상품 찜", description = "관심 상품을 찜한다. DRAFT 상태 상품은 찜할 수 없다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "찜 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 찜을 등록하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품이 없거나 비공개 상품임"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 찜한 상품임")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<WishResponse>> wish(
            Authentication authentication, @PathVariable Long userId, @Valid @RequestBody WishCreateRequest request) {
        requireSelf(authentication, userId);
        WishResponse response = wishService.wish(userId, request.productId());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(summary = "상품 찜 해제", description = "찜 목록에서 상품을 제거한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "해제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 찜을 해제하려 함"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "찜하지 않은 상품임")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> unwish(Authentication authentication, @PathVariable Long userId, @PathVariable Long id) {
        requireSelf(authentication, userId);
        wishService.unwish(userId, id);
        return ResponseEntity.noContent().build();
    }

    @Operation(
            summary = "찜 목록 조회",
            description = "찜한 상품 목록을 찜한 시각 최신순으로 조회한다. 찜한 이후 상품이 판매완료(SOLD) 등으로 "
                    + "바뀌어도 목록에서 제외하지 않고 현재 상태를 그대로 보여준다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 찜 목록을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<WishItemResponse>>> getWishList(
            Authentication authentication, @PathVariable Long userId, @PageableDefault(size = 20) Pageable pageable) {
        requireSelf(authentication, userId);
        PageResponse<WishItemResponse> response = wishService.getWishList(userId, pageable);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.WISH_FORBIDDEN);
        }
    }
}
