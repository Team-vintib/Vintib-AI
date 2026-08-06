package com.ssafy.backend.product.controller;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// 마이페이지 판매 상품 관리(MY-002). 기존 ProductController(/api/products, 공개 목록)와
// 경로 prefix가 달라 별도 컨트롤러로 분리한다(TryOnController/TryOnProfileController와 같은 이유).
@Tag(name = "상품(Products)", description = "상품 등록/조회, 브랜드/카테고리 마스터 조회 API")
@RestController
@RequestMapping("/api/users/{userId}/products")
@RequiredArgsConstructor
public class MyProductController {

    private final ProductService productService;

    @Operation(summary = "판매 상품 관리 목록 조회",
            description = "본인이 등록한 상품 전체를 등록일 최신순으로 조회한다. DRAFT 등 비공개 상태 상품도 포함된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 외 사용자의 상품 목록을 조회하려 함")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ProductResponse>>> getMyProducts(
            Authentication authentication, @PathVariable Long userId,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
        requireSelf(authentication, userId);
        Pageable pageable = PageRequest.of(page, size);
        return ResponseEntity.ok(ApiResponse.success(productService.getMyProducts(userId, pageable)));
    }

    // path의 userId가 인증된 본인이 아니면 존재 자체를 드러내지 않고 403으로 막는다(IDOR 방지).
    private void requireSelf(Authentication authentication, Long userId) {
        Long memberId = (Long) authentication.getPrincipal();
        if (!memberId.equals(userId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
    }
}
