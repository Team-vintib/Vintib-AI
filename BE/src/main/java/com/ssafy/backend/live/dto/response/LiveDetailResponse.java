package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 라이브 시청 화면 응답(LIVE-005). 방 정보와 편성된 상품을 한 번에 내려 화면 진입 시
 * 왕복을 늘리지 않는다.
 *
 * <p>영상 접속에 필요한 OpenVidu 토큰은 여기에 담지 않는다 — 토큰은 만료가 있고 시청자마다
 * 달라서 별도 발급 API(-449)가 맡는다.
 */
public record LiveDetailResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long id,

        @Schema(description = "호스트(판매자) 회원 ID", example = "1")
        Long hostId,

        @Schema(description = "호스트 닉네임", example = "빈티지장인")
        String hostNickname,

        @Schema(
                description = "호스트 프로필 이미지 URL. 등록하지 않았으면 null",
                example = "https://i15a108.p.ssafy.io/vintib-public/profile/1.jpg")
        String hostProfileImageUrl,

        @Schema(
                description = "**요청자가 이 방송의 호스트인지.** 비회원이거나 토큰이 없으면 false. "
                        + "판매자 전용 UI(종료·상품 전환 버튼)와 팔로우 버튼 노출을 이 값으로 가른다 — "
                        + "`hostId`를 클라이언트에서 직접 비교하면 회원 정보 복원이 늦을 때 판정이 뒤집힌다",
                example = "false")
        boolean isHost,

        @Schema(
                description = "이 방송의 시작 알림을 신청해 뒀는지(FE 요청 008 §3.2.1). "
                        + "**비회원이면 항상 false다.** 신청/취소는 "
                        + "`POST`/`DELETE /api/lives/{liveId}/reminders`",
                example = "false")
        boolean isReminderSet,

        @Schema(description = "방송명", example = "빈티지 데님 라이브")
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/101.jpg")
        String thumbnailUrl,

        @Schema(description = "방송 설명. 없으면 null", example = "90년대 리바이스 위주로 소개합니다")
        String description,

        @Schema(description = "방송 상태", example = "LIVE")
        LiveStatus status,

        @Schema(description = "방송 예정 시각. 즉시 개설이면 null", example = "2026-08-01T20:00:00")
        LocalDateTime scheduledAt,

        @Schema(description = "방송 시작 시각. 아직 시작 전이면 null", example = "2026-07-28T21:30:00")
        LocalDateTime startedAt,

        @Schema(description = "방송 종료 시각. 진행 중이면 null", example = "2026-07-28T22:30:00")
        LocalDateTime endedAt,

        @Schema(
                description = "최고 시청자 수. **누적 기록이며 방송이 끝나도 남는다.** "
                        + "현재 값은 currentViewerCount를 봐야 한다. 호스트를 세지 않는 기준은 동일하다",
                example = "152")
        int peakViewerCount,

        @Schema(
                description = "현재 동시 시청자 수. **화면 진입 시 이 값으로 시작하고, 이후 변화는 "
                        + "`/topic/lives/{liveId}/viewers` 구독으로 받는다.** 구독 직후 브로드캐스트가 "
                        + "오는 것은 보장되지 않으므로 초기값을 토픽에서 기다리면 안 된다.\n\n"
                        + "**호스트는 세지 않는다** — 판매자 혼자 방송 화면을 열어 둔 상태는 0명이다",
                example = "128")
        int currentViewerCount,

        @Schema(
                description = "지금 소개 중인 상품 ID(`NOW` 배지). **null이면 소개 중인 상품이 없다.** "
                        + "이후 전환은 `/topic/lives/{liveId}/product` 구독으로 받는다",
                example = "2001")
        Long currentProductId,

        @Schema(description = "편성된 상품 목록. 제외된 상품은 빠진다")
        List<LiveProductResponse> products,

        @Schema(
                description = "라이브 카테고리(대분류). **편성 상품에서 유도한 값이며 여러 개일 수 있다.** "
                        + "아우터·하의를 함께 파는 방송은 두 카테고리 모두에 잡힌다")
        List<LiveCategoryResponse> categories
) {

    /**
     * @param viewerId 조회한 회원 ID. <b>비회원이면 {@code null}</b>이며 이때 {@code isHost}는 false다.
     *                 시청 조회는 공개 엔드포인트라 토큰이 없을 수 있다
     */
    public static LiveDetailResponse of(
            Live live,
            List<LiveProductResponse> products,
            List<LiveCategoryResponse> categories,
            int currentViewerCount,
            Long viewerId,
            boolean reminderSet) {
        return new LiveDetailResponse(
                live.getId(),
                live.getHost().getId(),
                live.getHost().getNickname(),
                live.getHost().getProfileImageUrl(),
                live.isHostedBy(viewerId),
                reminderSet,
                live.getTitle(),
                live.getThumbnailUrl(),
                live.getDescription(),
                live.getStatus(),
                live.getScheduledAt(),
                live.getStartedAt(),
                live.getEndedAt(),
                live.getPeakViewerCount(),
                currentViewerCount,
                live.getCurrentProductId(),
                products,
                categories);
    }
}