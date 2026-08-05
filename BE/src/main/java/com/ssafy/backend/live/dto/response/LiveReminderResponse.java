package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 예약 라이브 알림 신청 상태(FE 요청 008 §3.2.1).
 *
 * <p>신청·취소가 모두 이 응답을 돌려주므로 FE는 응답 하나로 토글 상태를 확정할 수 있다 —
 * 성공 여부만 받고 화면에서 뒤집으면 재요청·중복 클릭 때 서버와 어긋난다.
 */
public record LiveReminderResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "알림 신청 상태. 신청하면 true, 취소하면 false", example = "true")
        boolean isReminderSet
) {

    public static LiveReminderResponse of(Long liveId, boolean set) {
        return new LiveReminderResponse(liveId, set);
    }
}
