package com.ssafy.backend.product.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "상품", description = "상품 등록/조회 API")
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService productService;

    @Operation(
            summary = "상품 기본 정보 저장",
            description = "카테고리/브랜드/제목/설명/상태등급/사이즈를 입력해 DRAFT 상태의 상품을 생성한다. "
                    + "판매 방식(상시 판매/경매)과 가격은 이 API에서 다루지 않고 이후 별도 API에서 설정한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<ProductResponse>> createProduct(
            Authentication authentication, @Valid @RequestBody ProductCreateRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductResponse response = productService.createProduct(sellerId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "판매 가격 설정 및 상시 판매 등록",
            description = "DRAFT 상태 상품에 가격을 설정해 상시 판매(ON_SALE) 상태로 전환한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "전환 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 DRAFT 상태가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @PatchMapping("/{id}/status")
    public ResponseEntity<ApiResponse<ProductResponse>> registerDirectSale(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody ProductStatusUpdateRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductResponse response = productService.registerDirectSale(sellerId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 목록 조회",
            description = "상시 판매/경매 여부와 관계없이 공개된 상품 목록을 최신순으로 조회한다. "
                    + "DRAFT/PRIVATE 상태 상품은 목록에서 제외한다. "
                    + "정렬은 항상 최신순(createdAt DESC)으로 고정되며, sort 파라미터를 보내도 무시된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ProductResponse>>> getProductList(
            @PageableDefault(size = 20) Pageable pageable) {
        PageResponse<ProductResponse> response = productService.getProductList(pageable);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 상세 조회",
            description = "상품 상세 정보를 조회한다. 비회원도 조회 가능하다. "
                    + "DRAFT/PRIVATE 상태 상품은 판매자 본인만 조회할 수 있으며, 그 외에는 존재하지 않는 것처럼 404를 반환한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품이 없거나 비공개 상품을 본인 외 사용자가 조회함")
    })
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ProductDetailResponse>> getProductDetail(
            Authentication authentication, @PathVariable Long id) {
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        ProductDetailResponse response = productService.getProductDetail(viewerId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
