package com.ssafy.backend.live.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.live.dto.request.LiveProductLinkRequest;
import com.ssafy.backend.live.dto.response.LiveProductResponse;
import com.ssafy.backend.live.service.LiveProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import lombok.RequiredArgsConstructor;
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

@Tag(name = "라이브(Lives)", description = "라이브 방송 개설/조회 API")
@RestController
@RequestMapping("/api/lives/{liveId}/products")
@RequiredArgsConstructor
public class LiveProductController {

    private final LiveProductService liveProductService;

    @Operation(
            summary = "라이브 상품 연결",
            description = "라이브에 판매할 상품을 건다. 방송 전·중 모두 가능하며 개수 제한은 없다. "
                    + "호스트 본인이 등록한 상품만 연결할 수 있고, 이미 연결된 상품은 중복 연결되지 않는다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "연결 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "요청값 검증 실패 또는 종료·취소된 방송"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아니거나 본인 상품이 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 또는 상품 없음"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 연결된 상품")
    })
    @SecurityRequirement(name = "bearerAuth")
    @PostMapping
    public ResponseEntity<ApiResponse<LiveProductResponse>> linkProduct(
            Authentication authentication,
            @PathVariable Long liveId,
            @Valid @RequestBody LiveProductLinkRequest request) {
        Long hostId = (Long) authentication.getPrincipal();
        LiveProductResponse response = liveProductService.linkProduct(hostId, liveId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @Operation(
            summary = "라이브 상품 연결 해제",
            description = "라이브에서 상품을 제외한다. 기록은 남기고 목록에서만 빠진다(다시보기 타임라인 근거).")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "204", description = "해제 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "종료·취소된 방송"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "본인 라이브가 아님"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음 또는 연결되지 않은 상품")
    })
    @SecurityRequirement(name = "bearerAuth")
    @DeleteMapping("/{productId}")
    public ResponseEntity<Void> unlinkProduct(
            Authentication authentication, @PathVariable Long liveId, @PathVariable Long productId) {
        Long hostId = (Long) authentication.getPrincipal();
        liveProductService.unlinkProduct(hostId, liveId, productId);
        return ResponseEntity.noContent().build();
    }

    @Operation(
            summary = "라이브 연결 상품 목록 조회",
            description = "현재 라이브에 연결된 상품을 노출 순서대로 반환한다. 제외된 상품은 빠진다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 필요"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "라이브 없음")
    })
    @SecurityRequirement(name = "bearerAuth")
    @GetMapping
    public ResponseEntity<ApiResponse<List<LiveProductResponse>>> getLinkedProducts(@PathVariable Long liveId) {
        List<LiveProductResponse> response = liveProductService.getLinkedProducts(liveId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
