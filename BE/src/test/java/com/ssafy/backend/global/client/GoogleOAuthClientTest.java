package com.ssafy.backend.global.client;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.config.GoogleOAuthConfig.GoogleOAuthProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

/** DeliveryTrackingClient와 달리 실패를 삼키지 않는다 — 로그인 실패를 조용히 넘기면 안 된다(SY039). */
class GoogleOAuthClientTest {

    private static final Duration TIMEOUT = Duration.ofSeconds(1);

    private GoogleOAuthClient clientWith(String baseUrl) {
        GoogleOAuthProperties properties =
                new GoogleOAuthProperties(baseUrl, "client-id", "client-secret", TIMEOUT, TIMEOUT);
        RestClient restClient = RestClient.builder().baseUrl(baseUrl).build();
        return new GoogleOAuthClient(restClient, properties);
    }

    @Test
    void 서버에_도달할_수_없으면_토큰_교환에서_예외를_던진다() {
        GoogleOAuthClient client = clientWith("https://127.0.0.1:1");

        assertThatThrownBy(() -> client.exchangeCode("code", "https://example.com/callback"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.GOOGLE_AUTH_FAILED);
    }

    @Test
    void 서버에_도달할_수_없으면_토큰_검증에서_예외를_던진다() {
        GoogleOAuthClient client = clientWith("https://127.0.0.1:1");

        assertThatThrownBy(() -> client.verifyIdToken("id-token"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.GOOGLE_AUTH_FAILED);
    }
}
