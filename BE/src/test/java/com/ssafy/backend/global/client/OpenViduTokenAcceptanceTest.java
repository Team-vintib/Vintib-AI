package com.ssafy.backend.global.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.ssafy.backend.global.config.OpenViduConfig.OpenViduProperties;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.junit.jupiter.api.Test;

/**
 * 우리가 만든 토큰을 <b>실제 LiveKit 서버가 받아주는지</b> 확인한다(-448/-449).
 *
 * <p>{@code OpenViduClientTest} 는 토큰의 <b>구조</b>만 본다 — 서명이 맞고 grant 가 들어 있는지.
 * 그것만으로는 "LiveKit 이 이 토큰을 실제로 통과시키는가"를 알 수 없다. claim 이름 하나만 달라도
 * 서버는 거절하는데, 그 사실은 브라우저가 붙는 순간에야 드러난다.
 *
 * <p><b>서버가 없으면 건너뛴다.</b> CI 에는 LiveKit 이 없고, 그 때문에 빌드가 깨지면 안 된다.
 * 로컬에서 {@code docker compose up -d livekit} 로 띄워 두면 자동으로 돈다.
 *
 * <p>키/시크릿은 {@code docker-compose.yml} 의 LiveKit 기본값과 같아야 한다. 다르면 서버가
 * 서명을 검증하지 못해 401 이 온다 — 그 경우도 이 테스트가 잡아낸다.
 */
class OpenViduTokenAcceptanceTest {

    private static final String LIVEKIT_URL = "http://localhost:7880";
    private static final String API_KEY = "devkey";
    private static final String API_SECRET = "devsecret-change-me-at-least-32-chars";

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(2))
            .build();

    private OpenViduClient client() {
        return new OpenViduClient(new OpenViduProperties(
                LIVEKIT_URL, LIVEKIT_URL, API_KEY, API_SECRET, Duration.ofHours(2)));
    }

    private HttpResponse<String> validate(String token) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(LIVEKIT_URL + "/rtc/validate?access_token=" + token))
                .timeout(Duration.ofSeconds(3))
                .GET()
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /** LiveKit 이 떠 있지 않으면 이 테스트들은 의미가 없다. */
    private void requireLiveKit() {
        boolean reachable;
        try {
            HttpRequest ping = HttpRequest.newBuilder()
                    .uri(URI.create(LIVEKIT_URL + "/"))
                    .timeout(Duration.ofSeconds(2))
                    .GET()
                    .build();
            http.send(ping, HttpResponse.BodyHandlers.discarding());
            reachable = true;
        } catch (Exception e) {
            reachable = false;
        }
        assumeTrue(reachable, "LiveKit 이 localhost:7880 에 없어 건너뛴다 (docker compose up -d livekit)");
    }

    @Test
    void 시청_토큰을_LiveKit이_받아준다() throws Exception {
        requireLiveKit();

        String token = client().issueViewerToken("live-101-accept", "guest-probe", "게스트");

        HttpResponse<String> response = validate(token);

        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(response.body()).contains("success");
    }

    @Test
    void 송출_토큰도_LiveKit이_받아준다() throws Exception {
        requireLiveKit();

        String token = client().issuePublisherToken("live-101-accept", "host-31", "빈티지장인");

        assertThat(validate(token).statusCode()).isEqualTo(200);
    }

    @Test
    void 시크릿이_다르면_LiveKit이_거절한다() throws Exception {
        requireLiveKit();

        // 서버와 백엔드의 시크릿이 어긋난 상황. 배포에서 가장 흔한 실수라 실제로 막히는지 본다.
        OpenViduClient wrongSecret = new OpenViduClient(new OpenViduProperties(
                LIVEKIT_URL, LIVEKIT_URL, API_KEY, "completely-different-secret-value-32", Duration.ofHours(2)));

        String token = wrongSecret.issueViewerToken("live-101-accept", "guest-probe", "게스트");

        assertThat(validate(token).statusCode()).isNotEqualTo(200);
    }
}
