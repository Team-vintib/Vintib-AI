package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 공개 라이브 목록의 카드 한 장(LIVE-005).
 *
 * <p>FE는 진행 중이면 {@code startedAt}, 예약이면 {@code scheduledAt}을 표시 시각으로 쓴다.
 */
public record LiveListItemResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "방송명", example = "90s 데님 재킷 라이브 셀렉션")
        String title,

        @Schema(description = "호스트 회원 ID", example = "31")
        Long hostId,

        @Schema(description = "호스트 닉네임", example = "빈티지장인")
        String hostNickname,

        @Schema(description = "썸네일 URL. 없으면 null이며 FE가 기본 이미지를 쓴다")
        String thumbnailUrl,

        @Schema(description = "방송 상태", example = "LIVE", allowableValues = {"LIVE", "SCHEDULED"})
        LiveStatus broadcastStatus,

        @Schema(
                description = "카테고리(대분류). **편성 상품에서 유도한 값이라 여러 개일 수 있다.** "
                        + "아우터·하의를 함께 파는 방송은 두 카테고리 모두에 잡힌다")
        List<LiveCategoryResponse> categories,

        @Schema(description = "방송 예정 시각. 진행 중이면 null", example = "2026-08-01T20:00:00")
        LocalDateTime scheduledAt,

        @Schema(description = "실제 시작 시각. 예약이면 null", example = "2026-07-29T11:02:10")
        LocalDateTime startedAt,

        @Schema(
                description = "현재 동시 시청자 수. **실시간 집계 값이다.** 예약 방송은 아직 아무도 "
                        + "보고 있지 않으므로 0이며, 진행 중인데 0이면 실제로 시청자가 없는 것이다",
                example = "128")
        int viewerCount,

        @Schema(
                description = "지금 소개 중인 상품 ID. 목록 카드에서 '지금 이 상품' 배지를 띄울 때 쓴다. "
                        + "**null이면 소개 중인 상품이 없다**",
                example = "2001")
        Long currentProductId
) {

    public static LiveListItemResponse of(
            Live live, List<LiveCategoryResponse> categories, int viewerCount) {
        return new LiveListItemResponse(
                live.getId(),
                live.getTitle(),
                live.getHost().getId(),
                live.getHost().getNickname(),
                live.getThumbnailUrl(),
                live.getStatus(),
                categories,
                live.getScheduledAt(),
                live.getStartedAt(),
                viewerCount,
                live.getCurrentProductId());
    }
}