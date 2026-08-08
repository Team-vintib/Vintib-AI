package com.ssafy.backend.auth.service;

import com.ssafy.backend.auth.dto.request.SignUpRequest;
import com.ssafy.backend.auth.dto.response.GoogleAuthResponse;
import com.ssafy.backend.auth.dto.response.GoogleOAuthConfigResponse;
import com.ssafy.backend.auth.dto.response.SignUpResponse;
import com.ssafy.backend.auth.dto.response.TokenResponse;
import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.global.client.GoogleIdentity;
import com.ssafy.backend.global.client.GoogleOAuthClient;
import com.ssafy.backend.global.config.GoogleOAuthConfig.GoogleOAuthProperties;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import java.time.Duration;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuthService {

    // 구글 연동 확인 대기 시간 — 사용자가 "연동하시겠습니까?" 확인을 미루면 대기 정보를 버린다.
    private static final Duration GOOGLE_LINK_TOKEN_TTL = Duration.ofMinutes(5);

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailVerificationService emailVerificationService;
    private final JwtTokenProvider jwtTokenProvider;
    private final StringRedisTemplate redisTemplate;
    private final GoogleOAuthClient googleOAuthClient;
    private final GoogleOAuthProperties googleOAuthProperties;

    public void checkEmailDuplicate(String email) {
        if (memberRepository.existsByEmail(normalizeEmail(email))) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }
    }

    public void sendEmailVerificationCode(String email) {
        String normalizedEmail = normalizeEmail(email);
        if (memberRepository.existsByEmail(normalizedEmail)) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }
        emailVerificationService.sendVerificationCode(normalizedEmail);
    }

    public String verifyEmailCode(String email, String code) {
        return emailVerificationService.verifyCode(normalizeEmail(email), code);
    }

    @Transactional
    public SignUpResponse signUp(SignUpRequest request) {
        String email = normalizeEmail(request.email());
        emailVerificationService.validateToken(request.verificationToken(), email);

        if (memberRepository.existsByEmail(email)) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }

        Member member = Member.builder()
                .email(email)
                .password(passwordEncoder.encode(request.password()))
                .name(request.name())
                .build();

        try {
            return SignUpResponse.from(memberRepository.save(member));
        } catch (DataIntegrityViolationException e) {
            // existsByEmail 체크와 save 사이의 동시 가입 race를 유니크 제약으로 최종 방어한다.
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }
    }

    public TokenResponse signIn(String email, String password) {
        Member member = memberRepository.findByEmail(normalizeEmail(email))
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_CREDENTIALS));

        if (!passwordEncoder.matches(password, member.getPassword())) {
            throw new CustomException(ErrorCode.INVALID_CREDENTIALS);
        }

        return issueTokens(member.getId(), member.getEmail());
    }

    public TokenResponse reissue(String refreshToken) {
        jwtTokenProvider.validateToken(refreshToken);
        Long memberId = jwtTokenProvider.getMemberId(refreshToken);

        String savedRefreshToken = redisTemplate.opsForValue().get(refreshTokenKey(memberId));
        if (savedRefreshToken == null || !savedRefreshToken.equals(refreshToken)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        return issueTokens(member.getId(), member.getEmail());
    }

    public void logout(Long memberId) {
        redisTemplate.delete(refreshTokenKey(memberId));
    }

    /**
     * 구글 로그인 client_id 공개 조회. 비밀값이 아니라 BE 설정값을 그대로 내려준다 —
     * FE가 별도 빌드 환경변수로 중복 관리하다 값 누락 사고가 났던 걸 계기로, BE 한 곳만 값의
     * 출처가 되도록 뺐다.
     */
    public GoogleOAuthConfigResponse getGoogleOAuthConfig() {
        return new GoogleOAuthConfigResponse(googleOAuthProperties.clientId());
    }

    /**
     * 구글 로그인. 이메일이 없으면 바로 가입시키고, 있는데 구글 연동이 안 돼 있으면
     * 토큰을 내주지 않고 연동 확인을 먼저 받는다({@link #confirmGoogleLink}).
     */
    @Transactional
    public GoogleAuthResponse signInWithGoogle(String code, String redirectUri) {
        String idToken = googleOAuthClient.exchangeCode(code, redirectUri);
        GoogleIdentity identity = googleOAuthClient.verifyIdToken(idToken);
        String email = normalizeEmail(identity.email());

        Optional<Member> existing = memberRepository.findByEmail(email);
        if (existing.isEmpty()) {
            Member member = memberRepository.save(
                    Member.ofGoogle(email, identity.name(), identity.googleId(), identity.pictureUrl()));
            return GoogleAuthResponse.login(
                    issueTokens(member.getId(), member.getEmail()), member.isOnboardingCompleted());
        }

        Member member = existing.get();
        if (identity.googleId().equals(member.getGoogleId())) {
            return GoogleAuthResponse.login(
                    issueTokens(member.getId(), member.getEmail()), member.isOnboardingCompleted());
        }

        String linkToken = UUID.randomUUID().toString();
        redisTemplate.opsForValue().set(
                googleLinkKey(linkToken), email + ":" + identity.googleId(), GOOGLE_LINK_TOKEN_TTL);
        return GoogleAuthResponse.linkRequired(linkToken, email);
    }

    /** 연동 확인 응답. 사용자가 거부하면 대기 정보만 지우고 로그인시키지 않는다. */
    @Transactional
    public GoogleAuthResponse confirmGoogleLink(String linkToken, boolean confirm) {
        String key = googleLinkKey(linkToken);
        String saved = redisTemplate.opsForValue().get(key);
        if (saved == null) {
            throw new CustomException(ErrorCode.GOOGLE_LINK_EXPIRED);
        }
        redisTemplate.delete(key);

        if (!confirm) {
            return GoogleAuthResponse.linkDeclined();
        }

        String[] parts = saved.split(":", 2);
        Member member = memberRepository.findByEmail(parts[0])
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        member.linkGoogleAccount(parts[1]);
        return GoogleAuthResponse.login(issueTokens(member.getId(), member.getEmail()), member.isOnboardingCompleted());
    }

    private String googleLinkKey(String linkToken) {
        return "auth:google-link:" + linkToken;
    }

    private TokenResponse issueTokens(Long memberId, String email) {
        String accessToken = jwtTokenProvider.createAccessToken(memberId, email);
        String refreshToken = jwtTokenProvider.createRefreshToken(memberId);

        redisTemplate.opsForValue().set(
                refreshTokenKey(memberId), refreshToken, jwtTokenProvider.getRefreshTokenValidity());

        return new TokenResponse(accessToken, refreshToken, memberId);
    }

    private String normalizeEmail(String email) {
        return email.trim().toLowerCase();
    }

    private String refreshTokenKey(Long memberId) {
        return "auth:refresh:" + memberId;
    }
}