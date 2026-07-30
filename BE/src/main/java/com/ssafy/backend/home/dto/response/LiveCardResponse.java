package com.ssafy.backend.home.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 홈/팔로잉 화면의 라이브 카드 공통 응답. (HOME-001 소유, HOME-002 재사용)
 *
 * <p>방송 상태({@code broadcastStatus})는 판매 상태와 구분되는 별도 축이다
 * (기능정의서 HOME-001: 상품 판매 상태와 방송 상태를 구분해 표시).
 * 2주차에 라이브 도메인 엔티티가 준비되면 그 상태 enum → 여기 문자열로 매핑한다.
 *
 * <p>FE는 진행 중이면 {@code startedAt}, 예약이면 {@code scheduledAt}을 카드 표시 시각으로 쓴다
 * (FE 요청 009-home-card-response-fields).
 */
public record LiveCardResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "방송명", example = "빈티지 데님 라이브")
        String title,

        @Schema(description = "판매자(호스트) 닉네임", example = "빈티지장인")
        String hostNickname,

        @Schema(description = "썸네일 URL", example = "https://picsum.photos/seed/live101/640/360")
        String thumbnailUrl,

        @Schema(description = "방송 상태", example = "LIVE", allowableValues = {"LIVE", "SCHEDULED"})
        String broadcastStatus,

        @Schema(description = "예약 방송 시작 예정 시각. 진행 중(LIVE)이면 null", example = "2026-08-01T20:00:00")
        LocalDateTime scheduledAt,

        @Schema(description = "실제 방송 시작 시각. 예약(SCHEDULED)이면 null", example = "2026-07-29T11:02:10")
        LocalDateTime startedAt,

        @Schema(description = "현재 시청자 수. 예약(SCHEDULED)이면 null", example = "152")
        Integer viewerCount,

        @Schema(description = "연결된 상품 수", example = "5")
        Integer productCount
) {
}