package com.ssafy.backend.live.dto.response;

import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

/**
 * 방송 상태 전이 브로드캐스트 payload — {@code /topic/lives/{liveId}/status}.
 *
 * <p>호스트가 방송을 시작·종료·취소하면 시청 중인 사람들이 즉시 알아야 한다. 이게 없으면
 * 호스트가 종료해도 시청 화면은 그대로 남고, 새로고침해야 404를 만난다(FE 요청 013).
 *
 * <p><b>얇게 유지한다.</b> 상세 응답을 통째로 쏘면 상품 목록·시청자 수까지 딸려 나가는데,
 * 상태가 바뀌는 순간에 그것들은 이미 다른 경로로 최신이다.
 */
public record LiveStatusResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(
                description = "바뀐 방송 상태. `ENDED`·`CANCELED`면 시청 화면을 종료 안내로 전환한다",
                example = "ENDED",
                allowableValues = {"LIVE", "ENDED", "CANCELED"})
        LiveStatus status,

        @Schema(description = "방송 시작 시각. 아직 시작 전이면 null", example = "2026-08-03T21:30:00")
        LocalDateTime startedAt,

        @Schema(description = "방송 종료 시각. 종료 전이면 null", example = "2026-08-03T22:40:00")
        LocalDateTime endedAt
) {

    public static LiveStatusResponse from(Live live) {
        return new LiveStatusResponse(
                live.getId(), live.getStatus(), live.getStartedAt(), live.getEndedAt());
    }

    /**
     * 전이 API 응답에서 만든다. 컨트롤러가 <b>커밋 이후</b>에 브로드캐스트하기 위해 쓰며,
     * 이 시점에는 엔티티 대신 이미 확정된 응답만 손에 있다.
     */
    public static LiveStatusResponse from(LiveResponse live) {
        return new LiveStatusResponse(
                live.id(), live.status(), live.startedAt(), live.endedAt());
    }
}
