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

        @Schema(
                description = "**요청자가 이 방송의 호스트인지.** 비회원이거나 토큰이 없으면 false. "
                        + "마이페이지 라이브 관리(MY-005)에서 '내 라이브' 배지·편집 진입을 이 값으로 가른다 — "
                        + "`hostId`를 클라이언트에서 직접 비교하면 회원 정보 복원이 늦을 때 판정이 뒤집힌다 "
                        + "(상세 조회의 `isHost`와 같은 이유)",
                example = "false")
        boolean isHost,

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

    /**
     * @param viewerId 조회한 회원 ID. <b>비회원이면 {@code null}</b>이며 이때 {@code isHost}는 false다.
     */
    public static LiveListItemResponse of(
            Live live, List<LiveCategoryResponse> categories, int viewerCount, Long viewerId) {
        return new LiveListItemResponse(
                live.getId(),
                live.getTitle(),
                live.getHost().getId(),
                live.getHost().getNickname(),
                live.isHostedBy(viewerId),
                live.getThumbnailUrl(),
                live.getStatus(),
                categories,
                live.getScheduledAt(),
                live.getStartedAt(),
                viewerCount,
                live.getCurrentProductId());
    }
}