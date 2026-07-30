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

        @Schema(description = "방송명", example = "빈티지 데님 라이브")
        String title,

        @Schema(description = "썸네일 URL", example = "https://cdn.example.com/live/101.jpg")
        String thumbnailUrl,

        @Schema(description = "방송 상태", example = "LIVE")
        LiveStatus status,

        @Schema(description = "방송 예정 시각. 즉시 개설이면 null", example = "2026-08-01T20:00:00")
        LocalDateTime scheduledAt,

        @Schema(description = "방송 시작 시각. 아직 시작 전이면 null", example = "2026-07-28T21:30:00")
        LocalDateTime startedAt,

        @Schema(description = "방송 종료 시각. 진행 중이면 null", example = "2026-07-28T22:30:00")
        LocalDateTime endedAt,

        @Schema(description = "최고 시청자 수", example = "152")
        int peakViewerCount,

        @Schema(description = "편성된 상품 목록. 제외된 상품은 빠진다")
        List<LiveProductResponse> products,

        @Schema(
                description = "라이브 카테고리(대분류). **편성 상품에서 유도한 값이며 여러 개일 수 있다.** "
                        + "아우터·하의를 함께 파는 방송은 두 카테고리 모두에 잡힌다")
        List<LiveCategoryResponse> categories
) {

    public static LiveDetailResponse of(
            Live live, List<LiveProductResponse> products, List<LiveCategoryResponse> categories) {
        return new LiveDetailResponse(
                live.getId(),
                live.getHost().getId(),
                live.getHost().getNickname(),
                live.getTitle(),
                live.getThumbnailUrl(),
                live.getStatus(),
                live.getScheduledAt(),
                live.getStartedAt(),
                live.getEndedAt(),
                live.getPeakViewerCount(),
                products,
                categories);
    }
}