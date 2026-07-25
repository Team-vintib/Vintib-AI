package com.ssafy.backend.auth.jwt;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Date;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class JwtTokenProvider {

    private final SecretKey key;
    private final Duration accessTokenValidity;
    private final Duration refreshTokenValidity;

    public JwtTokenProvider(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.access-token-validity}") long accessTokenValidityMillis,
            @Value("${jwt.refresh-token-validity}") long refreshTokenValidityMillis) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.accessTokenValidity = Duration.ofMillis(accessTokenValidityMillis);
        this.refreshTokenValidity = Duration.ofMillis(refreshTokenValidityMillis);
    }

    public String createAccessToken(Long memberId, String email) {
        return createToken(memberId, email, accessTokenValidity);
    }

    public String createRefreshToken(Long memberId) {
        return createToken(memberId, null, refreshTokenValidity);
    }

    public Duration getAccessTokenValidity() {
        return accessTokenValidity;
    }

    public Duration getRefreshTokenValidity() {
        return refreshTokenValidity;
    }

    public Long getMemberId(String token) {
        return Long.parseLong(parseClaims(token).getSubject());
    }

    public void validateToken(String token) {
        parseClaims(token);
    }

    private String createToken(Long memberId, String email, Duration validity) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + validity.toMillis());

        var builder = Jwts.builder()
                .subject(String.valueOf(memberId))
                .issuedAt(now)
                .expiration(expiry);
        if (email != null) {
            builder.claim("email", email);
        }
        return builder.signWith(key).compact();
    }

    private Claims parseClaims(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException e) {
            throw new CustomException(ErrorCode.EXPIRED_TOKEN);
        } catch (JwtException | IllegalArgumentException e) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
    }
}