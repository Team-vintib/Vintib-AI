package com.ssafy.backend.search.controller;

import com.ssafy.backend.global.response.ApiResponse;
import com.ssafy.backend.product.entity.SaleType;
import com.ssafy.backend.search.dto.request.SearchSort;
import com.ssafy.backend.search.dto.request.SearchType;
import com.ssafy.backend.search.dto.response.SearchResponse;
import com.ssafy.backend.search.service.SearchService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "검색(Search)", description = "상품·라이브·회원 통합 검색 API")
@Validated
@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SearchService searchService;

    @Operation(
            summary = "통합 검색",
            description = "검색어로 상품·라이브·회원을 함께 찾는다. **비회원도 조회할 수 있다.**\n\n"
                    + "`type`에 포함되지 않은 섹션은 **`null`로 내려간다** — 빈 배열(`content: []`)은 "
                    + "\"조회했지만 결과 0건\"이라는 뜻이라 구분이 필요하다.\n\n"
                    + "**상품·라이브 카드는 홈(`GET /api/home`)과 같은 타입이다.** FE가 같은 카드 "
                    + "컴포넌트를 그대로 쓸 수 있게 맞췄다.\n\n"
                    + "검색어는 **대소문자를 무시한 부분 일치**다. 상품은 상품명, 라이브는 방송명, "
                    + "회원은 **닉네임만** 대상으로 한다(이메일·실명은 검색되지 않는다). "
                    + "임시 저장(DRAFT) 상품과 종료·취소된 방송은 결과에 들어가지 않는다.\n\n"
                    + "필터(`categoryIds`·`conditionGrades`·`saleTypes`·`minPrice`·`maxPrice`)와 "
                    + "`sort`의 가격 정렬은 **상품에만 적용된다** — 라이브·회원에는 가격이 없다.\n\n"
                    + "`page`·`size`는 세 섹션에 동일하게 적용된다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "검색어 누락·공백이거나 허용되지 않는 type·sort·saleTypes 값")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<SearchResponse>> search(
            Authentication authentication,
            @Parameter(description = "검색어. 앞뒤 공백은 서버가 다듬는다", example = "빈티지")
            @RequestParam @NotBlank @Size(max = 100) String keyword,
            @Parameter(description = "검색 대상 탭. 생략하면 세 섹션을 모두 채운다")
            @RequestParam(defaultValue = "ALL") SearchType type,
            @Parameter(description = "카테고리 ID 목록(상품 전용). 소분류 ID 기준이다")
            @RequestParam(required = false) List<Long> categoryIds,
            @Parameter(description = "상태 등급 목록(상품 전용). 등급 체계가 미확정이라 자유 문자열이다")
            @RequestParam(required = false) List<String> conditionGrades,
            @Parameter(description = "판매 방식 목록(상품 전용)")
            @RequestParam(required = false) List<SaleType> saleTypes,
            @Parameter(description = "최저 가격(상품 전용)")
            @RequestParam(required = false) @Min(0) Long minPrice,
            @Parameter(description = "최고 가격(상품 전용)")
            @RequestParam(required = false) @Min(0) Long maxPrice,
            @RequestParam(defaultValue = "LATEST") SearchSort sort,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {

        // 공개 엔드포인트라 authentication 이 null 일 수 있다(비회원 검색).
        Long viewerId = authentication != null ? (Long) authentication.getPrincipal() : null;

        SearchResponse response = searchService.search(
                keyword, type, categoryIds, conditionGrades, saleTypes,
                minPrice, maxPrice, sort, page, size, viewerId);

        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
