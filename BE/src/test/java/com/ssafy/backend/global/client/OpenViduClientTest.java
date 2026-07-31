package com.ssafy.backend.global.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.config.OpenViduConfig.OpenViduProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import io.jsonwebtoken.Jwts;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;

/**
 * 접속 토큰 발급 테스트(-449).
 *
 * <p><b>이 테스트 자체가 계획서 Phase 4의 선행 확인 항목에 대한 답이다.</b> "토큰 발급에 미디어
 * 서버 호출이 필요한가"를 확인해야 했는데, <b>이 테스트에는 OpenVidu 서버가 없고 CI 에도 없다.</b>
 * 그런데도 토큰이 만들어지고 서명이 검증된다 — 로컬 서명이라는 뜻이고, 따라서 서버 구축(-448)이
 * 끝나기 전에 발급 로직을 완성할 수 있다.
 */
class OpenViduClientTest {

    private static final String API_KEY = "devkey";
    private static final String API_SECRET = "secret-that-is-long-enough-for-hmac-sha256";
    private static final String ROOM = "live-101-a3f9c1e2";

    private OpenViduClient clientWith(String url, String key, String secret) {
        // api-url 은 비워 둔다 — 지정하지 않으면 server-url 을 그대로 쓴다.
        return new OpenViduClient(new OpenViduProperties(url, null, key, secret, Duration.ofHours(2)));
    }

    private OpenViduClient configuredClient() {
        return clientWith("wss://openvidu.example.com", API_KEY, API_SECRET);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> videoGrantOf(String jwt) {
        var claims = Jwts.parser()
                .verifyWith(new SecretKeySpec(API_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"))
                .build()
                .parseSignedClaims(jwt)
                .getPayload();
        return (Map<String, Object>) claims.get("video");
    }

    @Test
    void 서버_없이_토큰이_발급되고_서명이_검증된다() {
        // 이 테스트가 도는 동안 OpenVidu 서버는 존재하지 않는다. 그런데도 통과한다는 것이
        // "토큰은 로컬 서명"이라는 확인이다.
        String jwt = configuredClient().issueViewerToken(ROOM, "guest-abc123", "게스트");

        var claims = Jwts.parser()
                .verifyWith(new SecretKeySpec(API_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"))
                .build()
                .parseSignedClaims(jwt)
                .getPayload();

        // iss 는 API key 다. LiveKit 서버가 이 값으로 어떤 키로 서명됐는지 판단한다.
        assertThat(claims.getIssuer()).isEqualTo(API_KEY);
        assertThat(claims.getSubject()).isEqualTo("guest-abc123");
        assertThat(claims.getExpiration()).isNotNull();
    }

    @Test
    void 시청_토큰은_발행_권한이_없다() {
        String jwt = configuredClient().issueViewerToken(ROOM, "viewer-42-abc123", "빈티지러버");

        Map<String, Object> video = videoGrantOf(jwt);

        // 토큰이 새어 나가도 남의 방송에 영상을 밀어 넣을 수 없어야 한다.
        assertThat(video).containsEntry("canPublish", false);
        assertThat(video).containsEntry("canSubscribe", true);
        assertThat(video).containsEntry("roomJoin", true);
        assertThat(video).containsEntry("room", ROOM);
    }

    @Test
    void 송출_토큰은_발행과_구독을_모두_허용한다() {
        String jwt = configuredClient().issuePublisherToken(ROOM, "host-31", "빈티지장인");

        Map<String, Object> video = videoGrantOf(jwt);

        assertThat(video).containsEntry("canPublish", true);
        assertThat(video).containsEntry("canSubscribe", true);
    }

    @Test
    void 토큰은_지정한_방에만_유효하다() {
        String jwt = configuredClient().issueViewerToken("live-999-zzz", "guest-x", "게스트");

        // room 이 grant 에 박혀 있어 다른 방송에 재사용할 수 없다.
        assertThat(videoGrantOf(jwt)).containsEntry("room", "live-999-zzz");
    }

    @Test
    void 설정이_비어_있으면_발급을_거부한다() {
        OpenViduClient unconfigured = clientWith("", "", "");

        assertThat(unconfigured.isConfigured()).isFalse();
        assertThatThrownBy(() -> unconfigured.issueViewerToken(ROOM, "guest-x", "게스트"))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.VIDEO_NOT_CONFIGURED);
    }

    @Test
    void 설정이_비어_있으면_room_정리는_조용히_넘어간다() {
        // 미디어 서버가 없는 환경에서도 방송 종료가 막히면 안 된다.
        OpenViduClient unconfigured = clientWith("", "", "");

        unconfigured.deleteRoom(ROOM);
    }

    @Test
    void 서버가_없어도_room_정리는_예외를_던지지_않는다() {
        // 설정은 돼 있는데 서버가 죽어 있는 상황. 종료가 실패하는 것보다 정리를 포기하는 편이 낫다.
        OpenViduClient client = clientWith("https://127.0.0.1:1", API_KEY, API_SECRET);

        client.deleteRoom(ROOM);
    }

    @Test
    void 만료_시각은_설정한_수명만큼_뒤다() {
        OpenViduClient client = configuredClient();
        var issuedAt = java.time.Instant.parse("2026-08-01T20:00:00Z");

        assertThat(client.expiresAt(issuedAt)).isEqualTo(java.time.Instant.parse("2026-08-01T22:00:00Z"));
    }
}
