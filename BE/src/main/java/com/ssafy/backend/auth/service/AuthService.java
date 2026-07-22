package com.ssafy.backend.auth.service;

import com.ssafy.backend.auth.dto.request.SignUpRequest;
import com.ssafy.backend.auth.dto.response.SignUpResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
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

    public void sendEmailVerificationCode(String email) {
        if (memberRepository.existsByEmail(email)) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }
        emailVerificationService.sendVerificationCode(email);
    }

    public String verifyEmailCode(String email, String code) {
        return emailVerificationService.verifyCode(email, code);
    }

    @Transactional
    public SignUpResponse signUp(SignUpRequest request) {
        emailVerificationService.validateToken(request.verificationToken(), request.email());

        if (memberRepository.existsByEmail(request.email())) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }

        Member member = Member.builder()
                .email(request.email())
                .password(passwordEncoder.encode(request.password()))
                .name(request.name())
                .build();

        return SignUpResponse.from(memberRepository.save(member));
    }
}