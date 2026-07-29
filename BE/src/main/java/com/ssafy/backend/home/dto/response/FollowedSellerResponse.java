package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 팔로잉 홈의 판매자 카드 응답(HOME-002). FE 요청 009-home-card-response-fields 기준.
 *
 * <p>라이브 관련 4개 필드({@code liveId}·{@code liveStatus}·{@code liveTitle}·{@code liveAt})는
 * 그 판매자가 지금 방송 중이거나 방송을 예약한 경우에만 채워진다. 넷 다 null이면 FE는 라이브
 * 배지 없이 판매자 정보만 표시한다.
 */
public record FollowedSellerResponse(

        @Schema(description = "판매자 회원 ID", example = "31")
        Long sellerId,

        @Schema(description = "판매자 표시명", example = "빈티지장인")
        String sellerName,

        @Schema(description = "프로필 이미지 URL", example = "https://picsum.photos/seed/seller31/200/200")
        String profileImageUrl,

        @Schema(description = "커버 이미지 URL", example = "https://picsum.photos/seed/seller31cover/800/300")
        String coverImageUrl,

        @Schema(description = "팔로워 수", example = "1284")
        Integer followerCount,

        @Schema(description = "판매 중인 상품 수", example = "37")
        Integer productCount,

        @Schema(description = "진행/예약 중인 라이브 ID. 없으면 null", example = "101")
        Long liveId,

        @Schema(
                description = "라이브 상태. 방송이 없으면 null",
                example = "LIVE",
                allowableValues = {"LIVE", "SCHEDULED"})
        String liveStatus,

        @Schema(description = "라이브 제목. 방송이 없으면 null", example = "빈티지 데님 라이브")
        String liveTitle,

        @Schema(description = "라이브 시작/예약 일시. 방송이 없으면 null", example = "2026-07-29T11:02:10")
        LocalDateTime liveAt
) {
}