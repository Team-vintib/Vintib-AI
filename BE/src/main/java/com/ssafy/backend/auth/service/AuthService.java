package com.ssafy.backend.auth.service;

import com.ssafy.backend.auth.dto.request.SignUpRequest;
import com.ssafy.backend.auth.dto.response.SignUpResponse;
import com.ssafy.backend.auth.dto.response.TokenResponse;
import com.ssafy.backend.auth.jwt.JwtTokenProvider;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
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

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailVerificationService emailVerificationService;
    private final JwtTokenProvider jwtTokenProvider;
    private final StringRedisTemplate redisTemplate;

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

    private TokenResponse issueTokens(Long memberId, String email) {
        String accessToken = jwtTokenProvider.createAccessToken(memberId, email);
        String refreshToken = jwtTokenProvider.createRefreshToken(memberId);

        redisTemplate.opsForValue().set(
                refreshTokenKey(memberId), refreshToken, jwtTokenProvider.getRefreshTokenValidity());

        return new TokenResponse(accessToken, refreshToken);
    }

    private String normalizeEmail(String email) {
        return email.trim().toLowerCase();
    }

    private String refreshTokenKey(Long memberId) {
        return "auth:refresh:" + memberId;
    }
}