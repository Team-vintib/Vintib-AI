package com.ssafy.backend.auth.jwt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import org.junit.jupiter.api.Test;

class JwtTokenProviderTest {

    private static final String SECRET = "test-secret-key-for-jwt-token-provider-unit-test-0123456789";

    @Test
    void 토큰을_생성하면_subject로_회원ID를_꺼낼_수_있다() {
        JwtTokenProvider provider = new JwtTokenProvider(SECRET, 60_000L, 60_000L);

        String token = provider.createAccessToken(1L, "user@example.com");

        assertThat(provider.getMemberId(token)).isEqualTo(1L);
    }

    @Test
    void 만료된_토큰을_검증하면_예외를_던진다() throws InterruptedException {
        JwtTokenProvider provider = new JwtTokenProvider(SECRET, 1L, 1L);
        String token = provider.createAccessToken(1L, "user@example.com");

        Thread.sleep(10);

        assertThatThrownBy(() -> provider.validateToken(token))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.EXPIRED_TOKEN);
    }

    @Test
    void 다른_키로_서명된_토큰은_검증에_실패한다() {
        JwtTokenProvider issuer = new JwtTokenProvider(SECRET, 60_000L, 60_000L);
        JwtTokenProvider verifier =
                new JwtTokenProvider("different-secret-key-that-does-not-match-issuer-key-000000", 60_000L, 60_000L);

        String token = issuer.createAccessToken(1L, "user@example.com");

        assertThatThrownBy(() -> verifier.validateToken(token))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_TOKEN);
    }
}