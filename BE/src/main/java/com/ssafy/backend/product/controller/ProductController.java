package com.ssafy.backend.product.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.product.dto.request.ProductCreateRequest;
import com.ssafy.backend.product.dto.request.ProductImageRegisterRequest;
import com.ssafy.backend.product.dto.request.ProductImageUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductImageUploadUrlRequest;
import com.ssafy.backend.product.dto.request.ProductListFilterParams;
import com.ssafy.backend.product.dto.request.ProductSortType;
import com.ssafy.backend.product.dto.request.ProductStatusUpdateRequest;
import com.ssafy.backend.product.dto.request.ProductUpdateRequest;
import com.ssafy.backend.product.dto.response.ProductAiModelCutResponse;
import com.ssafy.backend.product.dto.response.ProductDetailResponse;
import com.ssafy.backend.product.dto.response.ProductImageResponse;
import com.ssafy.backend.product.dto.response.ProductImageUploadUrlResponse;
import com.ssafy.backend.product.dto.response.ProductQualityInspectionResponse;
import com.ssafy.backend.product.dto.response.ProductResponse;
import com.ssafy.backend.product.service.ProductImageService;
import com.ssafy.backend.product.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@Tag(name = "상품(Products)", description = "상품 등록/조회, 브랜드/카테고리 마스터 조회 API")
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService productService;
    private final ProductImageService productImageService;

    @Operation(
            summary = "상품 기본 정보 저장",
            description = "카테고리/브랜드/제목/설명/상태등급/사이즈/색상/소재/실측/하자를 입력해 DRAFT 상태의 상품 생성. "
                    + "실측(measurements)과 하자(defects)는 선택 입력. "
                    + "판매 방식(상시 판매/경매)과 가격은 이 API에서 다루지 않고 이후 별도 API에서 설정.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<ProductResponse>> createProduct(
            Authentication authentication, @Valid @RequestBody ProductCreateRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductResponse response = productService.createProduct(sellerId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "판매 가격 설정 및 상시 판매 등록",
            description = "DRAFT(최초 등록) 또는 AUCTION_SCHEDULED(경매 예정 상품의 상시 판매 전환, "
                    + "상태 상품에 가격을 설정해 상시 판매(ON_SALE) 상태로 전환.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "전환 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "요청값 검증 실패 또는 DRAFT/AUCTION_SCHEDULED 상태가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
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
            summary = "경매 상품 등록 및 경매 전환",
            description = "DRAFT(최초 등록) 또는 ON_SALE(상시 판매 상품의 경매 전환) 상태 상품을 "
                    + "경매 예정(AUCTION_SCHEDULED) 상태로 전환. "
                    + "시작가·증액 단위·경매 시간은 경매 시작 전 별도 API로 설정한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "DRAFT/ON_SALE 상태가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}/auction-schedule")
    public ResponseEntity<ApiResponse<ProductResponse>> scheduleAuction(
            Authentication authentication, @PathVariable Long id) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductResponse response = productService.scheduleAuction(sellerId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 목록 조회",
            description = """
                    공개된 상품 목록 조회. DRAFT 상태 상품은 제외.
                    카테고리·상태등급·판매방식·가격 범위·판매자(sellerId) 필터를 조합할 수 있으며,
                    각 파라미터를 생략하면 해당 조건을 건너뜀. sellerId는 공개 프로필에서
                    특정 판매자의 상품만 보여줄 때 사용.
                    정렬: LATEST(기본값, 최신순) / PRICE_ASC(가격 낮은 순) / PRICE_DESC(가격 높은 순).
                    """)
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ProductResponse>>> getProductList(
            @RequestParam(required = false) List<Long> categoryIds,
            @RequestParam(required = false) List<String> conditionGrades,
            @RequestParam(required = false) com.ssafy.backend.product.entity.SaleType saleType,
            @RequestParam(required = false) Long minPrice,
            @RequestParam(required = false) Long maxPrice,
            @RequestParam(required = false) ProductSortType sort,
            @RequestParam(required = false) Long sellerId,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
        ProductListFilterParams filter =
                new ProductListFilterParams(categoryIds, conditionGrades, saleType, minPrice, maxPrice, sort, sellerId);
        Pageable pageable = PageRequest.of(page, size);
        PageResponse<ProductResponse> response = productService.getProductList(filter, pageable);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 상세 조회",
            description = "상품 상세 정보를 조회한다. 비회원도 조회 가능. "
                    + "DRAFT 상태 상품은 판매자 본인만 조회할 수 있으며, 그 외에는 존재하지 않는 것처럼 404를 반환.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품이 없거나 DRAFT 상품을 본인 외 사용자가 조회함")
    })
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ProductDetailResponse>> getProductDetail(
            Authentication authentication, @PathVariable Long id) {
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;
        ProductDetailResponse response = productService.getProductDetail(viewerId, id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "AI 착용컷 생성 상태/결과 조회",
            description = "판매자가 등록 시 AI 착용컷을 켠 상품의 생성 상태 조회. "
                    + "PENDING/PROCESSING이면 이 호출 시점에 AI 쪽 최신 상태 다시 확인.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @GetMapping("/{id}/ai-model-cut")
    public ResponseEntity<ApiResponse<ProductAiModelCutResponse>> getAiModelCutStatus(@PathVariable Long id) {
        ProductAiModelCutResponse response = productService.getAiModelCutStatus(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "하자 검수 상태/결과 조회",
            description = "앞/뒤 사진이 둘 다 등록되면 백그라운드로 도는 AI 하자 검수의 상태를 조회한다. "
                    + "PENDING/PROCESSING이면 이 호출 시점에 AI 쪽 최신 상태를 다시 확인해 반영한다. "
                    + "FE는 AI 게이트웨이를 직접 호출하지 않고 이 엔드포인트만 폴링한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @GetMapping("/{id}/quality-inspection")
    public ResponseEntity<ApiResponse<ProductQualityInspectionResponse>> getQualityInspectionStatus(
            @PathVariable Long id) {
        ProductQualityInspectionResponse response = productService.getQualityInspectionStatus(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 정보 수정",
            description = "제목/설명/카테고리/브랜드/상태등급/사이즈/색상/소재/실측/가격 부분 수정. 요청에 포함된 필드만 반영. "
                    + "하자(defects)는 null이면 미반영, 값을 보내면 기존 목록 전체 교체(빈 배열이면 전부 삭제). "
                    + "가격(price)은 상시 판매(saleType=DIRECT_SALE) 상품만 수정 가능. — 경매 상품에 보내면 400. "
                    + "DRAFT/ON_SALE/AUCTION_SCHEDULED 상태의 상품만 수정 가능.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 수정 불가 상태"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<ProductResponse>> updateProduct(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody ProductUpdateRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductResponse response = productService.updateProduct(sellerId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 삭제",
            description = "상품을 소프트 삭제(deleted_at 기록, DB row는 유지). "
                    + "DRAFT/ON_SALE 상태의 상품만 삭제할 수 있으며, 삭제 후에는 상세 조회 등에서 존재하지 않는 상품으로 취급.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "삭제 불가 상태"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduct(Authentication authentication, @PathVariable Long id) {
        Long sellerId = (Long) authentication.getPrincipal();
        productService.deleteProduct(sellerId, id);
        return ResponseEntity.noContent().build();
    }

    @Operation(
            summary = "상품 이미지 업로드 URL 발급",
            description = "S3에 이미지를 직접 업로드할 수 있는 presigned URL 발급(5분 만료). "
                    + "이미지 1개당 1회 호출하며, 업로드 후 등록 API를 호출해야 상품에 실제로 반영됨.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{id}/images/upload-url")
    public ResponseEntity<ApiResponse<ProductImageUploadUrlResponse>> createImageUploadUrl(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody ProductImageUploadUrlRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductImageUploadUrlResponse response = productImageService.createUploadUrl(sellerId, id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 이미지 등록",
            description = "presigned URL로 S3 업로드를 마친 이미지를 상품에 등록. "
                    + "업로드된 객체가 실제로 존재하는지, 용량 제한(10MB)을 넘지 않는지 서버가 다시 검증. "
                    + "상품당 이미지는 최대 10장까지 등록할 수 있다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "등록 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "업로드 미확인 또는 이미지 개수 초과"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/{id}/images")
    public ResponseEntity<ApiResponse<ProductImageResponse>> registerImage(
            Authentication authentication,
            @PathVariable Long id,
            @Valid @RequestBody ProductImageRegisterRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductImageResponse response = productImageService.registerImage(sellerId, id, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "상품 이미지 수정",
            description = "등록된 상품 이미지의 표시 순서(sortOrder)·대표 여부(isPrimary)를 수정. "
                    + "요청에 포함된 필드만 반영하는 부분 수정. isPrimary를 true로 바꾸면 같은 상품의 "
                    + "다른 이미지는 자동으로 대표에서 해제(상품당 대표 이미지는 항상 최대 1장).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "수정 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 또는 이미지 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PatchMapping("/{id}/images/{imageId}")
    public ResponseEntity<ApiResponse<ProductImageResponse>> updateImage(
            Authentication authentication,
            @PathVariable Long id,
            @PathVariable Long imageId,
            @Valid @RequestBody ProductImageUpdateRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductImageResponse response = productImageService.updateImage(sellerId, id, imageId, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(summary = "상품 이미지 삭제", description = "등록된 상품 이미지를 S3와 DB에서 함께 삭제.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "삭제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인이 등록한 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "상품 또는 이미지 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/{id}/images/{imageId}")
    public ResponseEntity<Void> deleteImage(
            Authentication authentication, @PathVariable Long id, @PathVariable Long imageId) {
        Long sellerId = (Long) authentication.getPrincipal();
        productImageService.deleteImage(sellerId, id, imageId);
        return ResponseEntity.noContent().build();
    }
}