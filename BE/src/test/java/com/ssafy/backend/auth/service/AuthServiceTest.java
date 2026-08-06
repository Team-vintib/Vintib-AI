package com.ssafy.backend.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.startsWith;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.auth.dto.request.SignUpRequest;
import com.ssafy.backend.auth.dto.response.GoogleAuthResponse;
import com.ssafy.backend.auth.dto.response.SignUpResponse;
import com.ssafy.backend.auth.dto.response.TokenResponse;
import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.global.client.GoogleIdentity;
import com.ssafy.backend.global.client.GoogleOAuthClient;
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
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.security.crypto.password.PasswordEncoder;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    private static final String EMAIL = "user@example.com";
    private static final String PASSWORD = "password12!";
    private static final Long MEMBER_ID = 1L;
    private static final String REFRESH_TOKEN_KEY = "auth:refresh:" + MEMBER_ID;
    private static final String GOOGLE_ID = "google-sub-123";
    private static final String GOOGLE_CODE = "auth-code";
    private static final String REDIRECT_URI = "https://example.com/callback";
    private static final String LINK_TOKEN = "link-token";
    private static final String LINK_TOKEN_KEY = "auth:google-link:" + LINK_TOKEN;

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
    private GoogleOAuthClient googleOAuthClient;

    @Mock
    private Member member;

    private AuthService authService;

    @BeforeEach
    void setUp() {
        authService = new AuthService(
                memberRepository, passwordEncoder, emailVerificationService, jwtTokenProvider, redisTemplate,
                googleOAuthClient);
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
        assertThat(response.id()).isEqualTo(MEMBER_ID);
        verify(valueOperations).set(eq(REFRESH_TOKEN_KEY), eq("refresh-token"), any(Duration.class));
    }

    @Test
    void 이미_가입된_이메일이면_중복확인에서_예외를_던진다() {
        when(memberRepository.existsByEmail(EMAIL)).thenReturn(true);

        assertThatThrownBy(() -> authService.checkEmailDuplicate("User@Example.com"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.DUPLICATE_EMAIL);
    }

    @Test
    void 사용_가능한_이메일이면_중복확인을_통과한다() {
        when(memberRepository.existsByEmail(EMAIL)).thenReturn(false);

        authService.checkEmailDuplicate("User@Example.com");

        verify(memberRepository).existsByEmail(EMAIL);
    }

    @Test
    void 로그인시_이메일_대소문자를_구분하지_않는다() {
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(member.getPassword()).thenReturn("encoded-password");
        when(passwordEncoder.matches(PASSWORD, "encoded-password")).thenReturn(true);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        TokenResponse response = authService.signIn(" User@Example.com ", PASSWORD);

        assertThat(response.accessToken()).isEqualTo("access-token");
        verify(memberRepository).findByEmail(EMAIL);
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
        assertThat(response.id()).isEqualTo(MEMBER_ID);
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
    void 회원가입시_이메일을_소문자로_정규화하여_저장한다() {
        SignUpRequest request = new SignUpRequest("User@Example.com", PASSWORD, "홍길동", "verification-token");
        when(memberRepository.existsByEmail(EMAIL)).thenReturn(false);
        when(passwordEncoder.encode(PASSWORD)).thenReturn("encoded-password");
        when(memberRepository.save(any(Member.class))).thenAnswer(invocation -> invocation.getArgument(0));

        SignUpResponse response = authService.signUp(request);

        assertThat(response.email()).isEqualTo(EMAIL);
        verify(emailVerificationService).validateToken("verification-token", EMAIL);
        verify(memberRepository).existsByEmail(EMAIL);
    }

    @Test
    void 저장_시점에_유니크_제약_위반이_발생하면_중복_이메일_예외로_변환한다() {
        SignUpRequest request = new SignUpRequest(EMAIL, PASSWORD, "홍길동", "verification-token");
        when(memberRepository.existsByEmail(EMAIL)).thenReturn(false);
        when(passwordEncoder.encode(PASSWORD)).thenReturn("encoded-password");
        when(memberRepository.save(any(Member.class)))
                .thenThrow(new DataIntegrityViolationException("duplicate key"));

        assertThatThrownBy(() -> authService.signUp(request))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.DUPLICATE_EMAIL);
    }

    @Test
    void 로그아웃하면_리프레시_토큰을_삭제한다() {
        authService.logout(MEMBER_ID);

        verify(redisTemplate).delete(REFRESH_TOKEN_KEY);
    }

    @Test
    void 이메일이_없으면_구글_신규가입후_로그인시킨다() {
        GoogleIdentity identity = new GoogleIdentity(GOOGLE_ID, EMAIL, "홍길동", "https://picture.example/1.jpg");
        when(googleOAuthClient.exchangeCode(GOOGLE_CODE, REDIRECT_URI)).thenReturn("id-token");
        when(googleOAuthClient.verifyIdToken("id-token")).thenReturn(identity);
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.empty());
        when(memberRepository.save(any(Member.class))).thenReturn(member);
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(member.isOnboardingCompleted()).thenReturn(false);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        GoogleAuthResponse response = authService.signInWithGoogle(GOOGLE_CODE, REDIRECT_URI);

        assertThat(response.status()).isEqualTo("LOGIN");
        assertThat(response.accessToken()).isEqualTo("access-token");
        assertThat(response.id()).isEqualTo(MEMBER_ID);
        assertThat(response.onboardingCompleted()).isFalse();
    }

    @Test
    void 이미_연동된_구글_계정이면_바로_로그인한다() {
        GoogleIdentity identity = new GoogleIdentity(GOOGLE_ID, EMAIL, "홍길동", "https://picture.example/1.jpg");
        when(googleOAuthClient.exchangeCode(GOOGLE_CODE, REDIRECT_URI)).thenReturn("id-token");
        when(googleOAuthClient.verifyIdToken("id-token")).thenReturn(identity);
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getGoogleId()).thenReturn(GOOGLE_ID);
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(member.isOnboardingCompleted()).thenReturn(true);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        GoogleAuthResponse response = authService.signInWithGoogle(GOOGLE_CODE, REDIRECT_URI);

        assertThat(response.status()).isEqualTo("LOGIN");
        verify(member, never()).linkGoogleAccount(any());
    }

    @Test
    void 이메일은_있는데_구글_연동이_안돼있으면_토큰없이_연동확인을_요청한다() {
        GoogleIdentity identity = new GoogleIdentity(GOOGLE_ID, EMAIL, "홍길동", "https://picture.example/1.jpg");
        when(googleOAuthClient.exchangeCode(GOOGLE_CODE, REDIRECT_URI)).thenReturn("id-token");
        when(googleOAuthClient.verifyIdToken("id-token")).thenReturn(identity);
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getGoogleId()).thenReturn(null);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        GoogleAuthResponse response = authService.signInWithGoogle(GOOGLE_CODE, REDIRECT_URI);

        assertThat(response.status()).isEqualTo("LINK_REQUIRED");
        assertThat(response.email()).isEqualTo(EMAIL);
        assertThat(response.accessToken()).isNull();
        verify(valueOperations).set(
                startsWith("auth:google-link:"),
                eq(EMAIL + ":" + GOOGLE_ID),
                any(Duration.class));
        verify(jwtTokenProvider, never()).createAccessToken(any(), any());
    }

    @Test
    void 연동을_확인하면_계정을_연동하고_로그인한다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(LINK_TOKEN_KEY)).thenReturn(EMAIL + ":" + GOOGLE_ID);
        when(memberRepository.findByEmail(EMAIL)).thenReturn(Optional.of(member));
        when(member.getId()).thenReturn(MEMBER_ID);
        when(member.getEmail()).thenReturn(EMAIL);
        when(member.isOnboardingCompleted()).thenReturn(false);
        when(jwtTokenProvider.createAccessToken(MEMBER_ID, EMAIL)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(MEMBER_ID)).thenReturn("refresh-token");
        when(jwtTokenProvider.getRefreshTokenValidity()).thenReturn(Duration.ofDays(14));

        GoogleAuthResponse response = authService.confirmGoogleLink(LINK_TOKEN, true);

        assertThat(response.status()).isEqualTo("LOGIN");
        verify(member).linkGoogleAccount(GOOGLE_ID);
        verify(redisTemplate).delete(LINK_TOKEN_KEY);
    }

    @Test
    void 연동을_거부하면_로그인하지_않는다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(LINK_TOKEN_KEY)).thenReturn(EMAIL + ":" + GOOGLE_ID);

        GoogleAuthResponse response = authService.confirmGoogleLink(LINK_TOKEN, false);

        assertThat(response.status()).isEqualTo("LINK_DECLINED");
        verify(memberRepository, never()).findByEmail(any());
        verify(redisTemplate).delete(LINK_TOKEN_KEY);
    }

    @Test
    void 연동_토큰이_만료됐으면_예외를_던진다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(LINK_TOKEN_KEY)).thenReturn(null);

        assertThatThrownBy(() -> authService.confirmGoogleLink(LINK_TOKEN, true))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.GOOGLE_LINK_EXPIRED);
    }
}