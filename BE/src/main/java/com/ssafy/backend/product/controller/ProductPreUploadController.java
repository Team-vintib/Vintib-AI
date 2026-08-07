package com.ssafy.backend.product.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.product.dto.request.ProductClassifyTriggerRequest;
import com.ssafy.backend.product.dto.request.ProductPreUploadUrlRequest;
import com.ssafy.backend.product.dto.response.ProductClassifyJobResponse;
import com.ssafy.backend.product.dto.response.ProductClassifyStatusResponse;
import com.ssafy.backend.product.dto.response.ProductPreUploadUrlResponse;
import com.ssafy.backend.product.service.ProductPreUploadService;
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

/**
 * 상품 생성 전(사전업로드) 카테고리·색상 AI 분류 API. 상품 등록 위저드에서 판매자가 사진을
 * 올리는 즉시 폼을 프리필하기 위한 것이라 {@link ProductController}의 하자검수/착용컷
 * 패턴(상품 생성 후 트리거, Product 엔티티에 job 상태 저장)과 의도적으로 다르다 — 완전
 * 무상태 프록시로, jobId는 FE가 직접 들고 있는다(`docs/requests/BE/
 * 045-classify-pre-upload-integration.md`).
 */
@Tag(name = "상품 사전업로드(Product Pre-upload)", description = "상품 생성 전 사진으로 AI 카테고리·색상 분류를 미리 받는다")
@RestController
@RequestMapping("/api/products/pre-upload")
@RequiredArgsConstructor
public class ProductPreUploadController {

    private final ProductPreUploadService preUploadService;

    @Operation(
            summary = "사전업로드용 이미지 업로드 URL 발급",
            description = "상품이 아직 생성되지 않은 시점에, 분류에 쓸 사진 1장을 S3에 올릴 presigned URL을 발급한다(5분 만료).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발급 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "지원하지 않는 이미지 형식"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/upload-url")
    public ResponseEntity<ApiResponse<ProductPreUploadUrlResponse>> createUploadUrl(
            Authentication authentication, @Valid @RequestBody ProductPreUploadUrlRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductPreUploadUrlResponse response = preUploadService.createUploadUrl(sellerId, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "분류 job 트리거",
            description = "사전업로드한 이미지 key로 AI 카테고리·색상 분류 job을 접수하고 jobId를 돌려준다. "
                    + "이 jobId는 서버에 저장하지 않으니 FE가 직접 들고 있다가 상태 조회에 써야 한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "접수 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400", description = "업로드가 확인되지 않은 key"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "503", description = "AI 분류 요청 실패")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping("/classify")
    public ResponseEntity<ApiResponse<ProductClassifyJobResponse>> triggerClassify(
            Authentication authentication, @Valid @RequestBody ProductClassifyTriggerRequest request) {
        Long sellerId = (Long) authentication.getPrincipal();
        ProductClassifyJobResponse response = preUploadService.triggerClassify(sellerId, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Operation(
            summary = "분류 job 상태/결과 조회",
            description = "jobId로 AI 분류 결과를 조회한다. PENDING/PROCESSING이면 이 호출 시점에 AI 쪽 최신 상태를 다시 "
                    + "확인한다. 완료 시 categoryId는 BE가 (성별×소분류) 조회표로 미리 계산해 함께 내려준다"
                    + "(성별 미확정 시 남성 기준 우선).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "503", description = "AI 분류 상태 조회 실패")
    })
    @GetMapping("/classify/{jobId}")
    public ResponseEntity<ApiResponse<ProductClassifyStatusResponse>> getClassifyStatus(@PathVariable String jobId) {
        ProductClassifyStatusResponse response = preUploadService.getClassifyStatus(jobId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
