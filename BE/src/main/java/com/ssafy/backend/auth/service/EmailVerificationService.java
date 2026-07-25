package com.ssafy.backend.auth.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class EmailVerificationService {

    private static final Duration CODE_TTL = Duration.ofMinutes(5);
    private static final Duration RESEND_COOLDOWN = Duration.ofSeconds(60);
    private static final Duration SEND_COUNT_WINDOW = Duration.ofHours(1);
    private static final int MAX_SEND_COUNT_PER_HOUR = 5;
    private static final int MAX_VERIFY_ATTEMPTS = 5;
    private static final Duration TOKEN_TTL = Duration.ofMinutes(30);

    private final StringRedisTemplate redisTemplate;
    private final JavaMailSender mailSender;

    public void sendVerificationCode(String email) {
        String cooldownKey = cooldownKey(email);
        if (Boolean.TRUE.equals(redisTemplate.hasKey(cooldownKey))) {
            throw new CustomException(ErrorCode.TOO_MANY_VERIFICATION_REQUESTS);
        }

        String sendCountKey = sendCountKey(email);
        String sendCountValue = redisTemplate.opsForValue().get(sendCountKey);
        long sendCount = sendCountValue == null ? 0 : Long.parseLong(sendCountValue);
        if (sendCount >= MAX_SEND_COUNT_PER_HOUR) {
            throw new CustomException(ErrorCode.TOO_MANY_VERIFICATION_REQUESTS);
        }

        String code = generateCode();
        sendMail(email, code);

        // 메일 발송이 성공한 뒤에만 Redis 상태를 반영한다.
        // 먼저 반영하면 발송 실패 시에도 쿨다운/횟수 제한이 걸려 사용자가 코드 없이 묶인다.
        redisTemplate.opsForValue().set(codeKey(email), code, CODE_TTL);
        redisTemplate.delete(attemptsKey(email));
        redisTemplate.opsForValue().set(cooldownKey, "1", RESEND_COOLDOWN);

        Long newSendCount = redisTemplate.opsForValue().increment(sendCountKey);
        if (newSendCount != null && newSendCount == 1L) {
            redisTemplate.expire(sendCountKey, SEND_COUNT_WINDOW);
        }
    }

    public String verifyCode(String email, String code) {
        String attemptsKey = attemptsKey(email);
        Long attempts = redisTemplate.opsForValue().increment(attemptsKey);
        if (attempts != null && attempts == 1L) {
            redisTemplate.expire(attemptsKey, CODE_TTL);
        }
        if (attempts != null && attempts > MAX_VERIFY_ATTEMPTS) {
            redisTemplate.delete(codeKey(email));
            throw new CustomException(ErrorCode.TOO_MANY_VERIFICATION_ATTEMPTS);
        }

        String codeKey = codeKey(email);
        String savedCode = redisTemplate.opsForValue().get(codeKey);
        if (savedCode == null || !savedCode.equals(code)) {
            throw new CustomException(ErrorCode.INVALID_VERIFICATION_CODE);
        }

        redisTemplate.delete(codeKey);
        redisTemplate.delete(attemptsKey);

        String token = UUID.randomUUID().toString();
        redisTemplate.opsForValue().set(tokenKey(token), email, TOKEN_TTL);
        return token;
    }

    public void validateToken(String token, String email) {
        String tokenKey = tokenKey(token);
        String savedEmail = redisTemplate.opsForValue().get(tokenKey);
        if (savedEmail == null || !savedEmail.equals(email)) {
            throw new CustomException(ErrorCode.EMAIL_VERIFICATION_REQUIRED);
        }
        redisTemplate.delete(tokenKey);
    }

    private void sendMail(String email, String code) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(email);
        message.setSubject("[빈티지 경매] 이메일 인증 코드");
        message.setText("인증 코드: " + code + "\n5분 이내에 입력해주세요.");
        mailSender.send(message);
    }

    private String generateCode() {
        SecureRandom random = new SecureRandom();
        return String.format("%06d", random.nextInt(1_000_000));
    }

    private String codeKey(String email) {
        return "email:verify:code:" + email;
    }

    private String attemptsKey(String email) {
        return "email:verify:attempts:" + email;
    }

    private String cooldownKey(String email) {
        return "email:verify:cooldown:" + email;
    }

    private String sendCountKey(String email) {
        return "email:verify:sendcount:" + email;
    }

    private String tokenKey(String token) {
        return "email:verify:token:" + token;
    }
}