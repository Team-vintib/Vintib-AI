package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * 팔로잉 콘텐츠 조회(HOME-002) 응답. 팔로우한 회원의 라이브·상품 목록을 담는다.
 *
 * <p>팔로우가 없거나 노출할 콘텐츠가 없으면 {@code empty=true}로 내려, FE가 추천 회원 등
 * 대체 UI를 띄우도록 한다(추천 회원 목록 자체는 이번 범위 밖 — 여력 시 2주차).
 * 카드 DTO는 HOME-001이 소유한 공통 타입을 재사용한다.
 *
 * <p><b>{@code products}는 "팔로우한 판매자의 상품"이다</b> — 추천 상품이 아니다
 * (FE 요청 009-home-card-response-fields 요청 7의 1번안). 개인화 추천(REC-001)은
 * 별도 응답으로 분리한다. FE는 이 섹션의 제목을 그에 맞게 표기하면 된다.
 */
public record FollowingContentResponse(

        @Schema(
                description = "팔로우한 회원의 콘텐츠가 없는지 여부. "
                        + "true면 lives·products·followedSellers가 모두 비어 있다",
                example = "false")
        boolean empty,

        @Schema(description = "팔로우한 회원의 라이브 목록")
        List<LiveCardResponse> lives,

        @Schema(description = "팔로우한 회원의 상품 목록. 추천 상품이 아니다")
        List<ProductCardResponse> products,

        @Schema(description = "내가 팔로우한 판매자 목록")
        List<FollowedSellerResponse> followedSellers
) {
}