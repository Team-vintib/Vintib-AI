package com.ssafy.backend.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.auth.dto.response.TokenResponse;
import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.Duration;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.security.crypto.password.PasswordEncoder;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    private static final String EMAIL = "user@example.com";
    private static final String PASSWORD = "password12!";
    private static final Long MEMBER_ID = 1L;
    private static final String REFRESH_TOKEN_KEY = "auth:refresh:" + MEMBER_ID;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private EmailVerificationService emailVerificationService;

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @Mock
    private Member member;

    private AuthService authService;

    @BeforeEach
    void setUp() {
        authService = new AuthService(
                memberRepository, passwordEncoder, emailVerificationService, jwtTokenProvider, redisTemplate);
    }

    @Test
    void 이메일과_비밀번호가_일치하면_토큰을_발급한다() {
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(member.getPassword()).thenReturn("encoded-password");
        when(passwordEncoder.matches(PASSWORD, "encoded-password")).thenReturn(true);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        TokenResponse response = authService.signIn(EMAIL, PASSWORD);

        assertThat(response.accessToken()).isEqualTo("access-token");
        assertThat(response.refreshToken()).isEqualTo("refresh-token");
        verify(valueOperations).set(eq(REFRESH_TOKEN_KEY), eq("refresh-token"), any(Duration.class));
    }

    @Test
    void 존재하지_않는_이메일이면_예외를_던진다() {
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> authService.signIn(EMAIL, PASSWORD))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_CREDENTIALS);
    }

    @Test
    void 비밀번호가_일치하지_않으면_예외를_던진다() {
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getPassword()).thenReturn("encoded-password");
        when(passwordEncoder.matches(PASSWORD, "encoded-password")).thenReturn(false);

        assertThatThrownBy(() -> authService.signIn(EMAIL, PASSWORD))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_CREDENTIALS);
    }

    @Test
    void Redis에_저장된_리프레시_토큰과_일치하면_재발급한다() {
        when(jwtTokenProvider.getMemberId("refresh-token")).thenReturn(MEMBER_ID);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(REFRESH_TOKEN_KEY)).thenReturn("refresh-token");
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("new-access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("new-refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));

        TokenResponse response = authService.reissue("refresh-token");

        assertThat(response.accessToken()).isEqualTo("new-access-token");
        assertThat(response.refreshToken()).isEqualTo("new-refresh-token");
    }

    @Test
    void Redis에_저장된_리프레시_토큰과_다르면_예외를_던진다() {
        when(jwtTokenProvider.getMemberId("refresh-token")).thenReturn(MEMBER_ID);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(REFRESH_TOKEN_KEY)).thenReturn("other-refresh-token");

        assertThatThrownBy(() -> authService.reissue("refresh-token"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_TOKEN);
    }

    @Test
    void 로그아웃하면_리프레시_토큰을_삭제한다() {
        authService.logout(MEMBER_ID);

        verify(redisTemplate).delete(REFRESH_TOKEN_KEY);
    }
}