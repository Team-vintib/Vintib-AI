package com.ssafy.backend.home.dto.response;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
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

        @Schema(
                description = "판매자(호스트) 회원 ID. 카드에서 판매자 프로필로 이동할 때 쓴다 "
                        + "(FE 요청 004 §3.1)",
                example = "10")
        Long hostId,

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

    /**
     * 라이브 엔티티에서 카드를 만든다. 홈(HOME-001)과 팔로잉 홈(HOME-002)이 같은 규칙으로 그려야
     * 해서 조립을 여기 한 곳에 둔다.
     *
     * <p><b>진행 중이 아니면 {@code viewerCount}는 null이다.</b> 예약 방송의 0명과 "집계 대상이
     * 아님"은 다른 뜻인데, 0으로 내리면 FE가 "아무도 안 보는 방송"으로 표시한다.
     *
     * @param viewerCount  현재 시청자 수(진행 중일 때만 의미 있음)
     * @param productCount 편성 상품 수
     */
    public static LiveCardResponse of(Live live, int viewerCount, int productCount) {
        boolean onAir = live.getStatus() == LiveStatus.LIVE;
        return new LiveCardResponse(
                live.getId(),
                live.getTitle(),
                live.getHost().getId(),
                live.getHost().getNickname(),
                live.getThumbnailUrl(),
                live.getStatus().name(),
                live.getScheduledAt(),
                live.getStartedAt(),
                onAir ? viewerCount : null,
                productCount);
    }
}