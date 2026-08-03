package com.ssafy.backend.search.dto.response;

import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 통합 검색 응답(SEARCH-001/002).
 *
 * <p><b>상품·라이브 카드는 홈에서 쓰는 것과 같은 타입이다.</b> 검색 결과용 DTO를 따로 만들면
 * FE가 같은 카드 컴포넌트에 두 가지 모양을 먹여야 하고, 필드가 하나 늘 때마다 두 곳을 고쳐야
 * 한다. 검색은 "같은 카드를 다른 조건으로 찾아 주는 것"이지 다른 물건을 주는 게 아니다.
 *
 * <p><b>{@code null}과 빈 배열은 뜻이 다르다.</b> {@code type}에 포함되지 않은 섹션은
 * {@code null}(조회하지 않음), 조회했지만 결과가 없으면 {@code content}가 빈 배열이다.
 */
public record SearchResponse(

        @Schema(description = "상품 결과. `type`이 ALL·PRODUCT가 아니면 null")
        PageResponse<ProductCardResponse> products,

        @Schema(description = "라이브 결과. `type`이 ALL·LIVE가 아니면 null")
        PageResponse<LiveCardResponse> lives,

        @Schema(description = "회원 결과. `type`이 ALL·USER가 아니면 null")
        PageResponse<UserSearchItemResponse> users
) {
}
