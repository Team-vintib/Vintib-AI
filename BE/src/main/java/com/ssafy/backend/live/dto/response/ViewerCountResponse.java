package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 시청자 수 변화 알림. {@code /topic/lives/{liveId}/viewers} 로 나간다.
 *
 * <p><b>{@code liveId} 를 함께 담는 이유.</b> FE 가 여러 방송 토픽을 한 연결에서 구독할 수 있고,
 * 그때 어느 방송의 값인지 payload 만 보고 판단할 수 있어야 한다. destination 문자열을 파싱해
 * 알아내게 만들면 목적지 규약이 바뀔 때 FE 가 같이 깨진다.
 */
public record ViewerCountResponse(

        @Schema(description = "라이브 ID", example = "101")
        Long liveId,

        @Schema(description = "현재 동시 시청자 수. 0일 수 있다", example = "128")
        int viewerCount
) {

    public static ViewerCountResponse of(Long liveId, int viewerCount) {
        return new ViewerCountResponse(liveId, viewerCount);
    }
}
