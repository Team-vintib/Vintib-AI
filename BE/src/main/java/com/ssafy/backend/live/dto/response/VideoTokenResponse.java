package com.ssafy.backend.live.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

/**
 * 영상 접속 토큰(LIVE-005 / -449).
 *
 * <p><b>{@code serverUrl} 을 함께 내리는 이유.</b> FE 가 환경별 미디어 서버 주소를 따로 관리하면
 * 배포 환경이 늘 때마다 두 곳(BE 설정·FE 빌드 변수)을 맞춰야 하고, 어긋나면 "토큰은 유효한데
 * 접속이 안 되는" 형태로 드러나 원인을 찾기 어렵다. 토큰과 주소는 한 쌍으로 움직인다.
 */
public record VideoTokenResponse(

        @Schema(description = "LiveKit room 이름. 방송마다 다르다", example = "live-101-a3f9c1e2")
        String roomName,

        @Schema(description = "접속 토큰(JWT). 그대로 LiveKit 클라이언트에 넘긴다")
        String token,

        @Schema(
                description = "미디어 서버 주소. LiveKit 클라이언트는 wss로 접속한다",
                example = "wss://openvidu.i15a108.p.ssafy.io")
        String serverUrl,

        @Schema(
                description = "이 토큰의 역할. **서버가 정한다** — 호스트 본인이면 PUBLISHER, "
                        + "그 외에는 비회원 포함 VIEWER다. 클라이언트가 고를 수 없다",
                example = "VIEWER",
                allowableValues = {"PUBLISHER", "VIEWER"})
        VideoRole role,

        @Schema(description = "토큰 만료 시각. 방송이 더 길어지면 만료 전에 재발급받아야 한다")
        Instant expiresAt
) {

    public enum VideoRole {
        /** 송출자(호스트). 발행·구독 모두 허용. */
        PUBLISHER,
        /** 시청자. 구독만 허용. */
        VIEWER
    }

    public static VideoTokenResponse of(
            String roomName, String token, String serverUrl, VideoRole role, Instant expiresAt) {
        return new VideoTokenResponse(roomName, token, serverUrl, role, expiresAt);
    }
}
