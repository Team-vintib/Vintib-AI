package com.ssafy.backend.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import java.time.Duration;
import java.util.Properties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

@ExtendWith(MockitoExtension.class)
class EmailVerificationServiceTest {

    private static final String EMAIL = "user@example.com";
    private static final String CODE_KEY = "email:verify:code:" + EMAIL;
    private static final String ATTEMPTS_KEY = "email:verify:attempts:" + EMAIL;
    private static final String COOLDOWN_KEY = "email:verify:cooldown:" + EMAIL;
    private static final String SEND_COUNT_KEY = "email:verify:sendcount:" + EMAIL;

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @Mock
    private JavaMailSender mailSender;

    @Mock
    private TemplateEngine templateEngine;

    private EmailVerificationService emailVerificationService;

    @BeforeEach
    void setUp() {
        emailVerificationService = new EmailVerificationService(redisTemplate, mailSender, templateEngine);
    }

    private static MimeMessage mimeMessage() {
        return new MimeMessage(Session.getInstance(new Properties()));
    }

    @Test
    void 재발송_쿨다운_중이면_예외를_던진다() {
        when(redisTemplate.hasKey(COOLDOWN_KEY)).thenReturn(true);

        assertThatThrownBy(() -> emailVerificationService.sendVerificationCode(EMAIL))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TOO_MANY_VERIFICATION_REQUESTS);
    }

    @Test
    void 윈도우_내_발송_횟수를_초과하면_메일을_보내지_않고_예외를_던진다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(SEND_COUNT_KEY)).thenReturn("5");

        assertThatThrownBy(() -> emailVerificationService.sendVerificationCode(EMAIL))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TOO_MANY_VERIFICATION_REQUESTS);

        verify(mailSender, never()).send(any(MimeMessage.class));
    }

    @Test
    void 메일_발송에_실패하면_Redis_상태를_남기지_않는다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(SEND_COUNT_KEY)).thenReturn(null);
        when(templateEngine.process(anyString(), any(Context.class))).thenReturn("<html></html>");
        when(mailSender.createMimeMessage()).thenReturn(mimeMessage());
        doThrow(new MailSendException("smtp error")).when(mailSender).send(any(MimeMessage.class));

        assertThatThrownBy(() -> emailVerificationService.sendVerificationCode(EMAIL))
                .isInstanceOf(MailSendException.class);

        verify(valueOperations, never()).set(eq(CODE_KEY), any(), any(Duration.class));
        verify(valueOperations, never()).set(eq(COOLDOWN_KEY), any(), any(Duration.class));
        verify(redisTemplate, never()).delete(ATTEMPTS_KEY);
    }

    @Test
    void 인증코드가_다르면_예외를_던진다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.increment(ATTEMPTS_KEY)).thenReturn(1L);
        when(valueOperations.get(CODE_KEY)).thenReturn("123456");

        assertThatThrownBy(() -> emailVerificationService.verifyCode(EMAIL, "000000"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.INVALID_VERIFICATION_CODE);
    }

    @Test
    void 인증코드가_일치하면_토큰을_발급한다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.increment(ATTEMPTS_KEY)).thenReturn(1L);
        when(valueOperations.get(CODE_KEY)).thenReturn("123456");

        String token = emailVerificationService.verifyCode(EMAIL, "123456");

        assertThat(token).isNotBlank();
        verify(redisTemplate).delete(CODE_KEY);
        verify(redisTemplate).delete(ATTEMPTS_KEY);
        verify(valueOperations).set(eq("email:verify:token:" + token), eq(EMAIL), any(Duration.class));
    }

    @Test
    void 시도_횟수를_초과하면_코드를_무효화하고_예외를_던진다() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.increment(ATTEMPTS_KEY)).thenReturn(6L);

        assertThatThrownBy(() -> emailVerificationService.verifyCode(EMAIL, "000000"))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.TOO_MANY_VERIFICATION_ATTEMPTS);

        verify(redisTemplate).delete(CODE_KEY);
    }

    @Test
    void 토큰이_이메일과_일치하지_않으면_예외를_던진다() {
        String token = "some-token";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("email:verify:token:" + token)).thenReturn("other@example.com");

        assertThatThrownBy(() -> emailVerificationService.validateToken(token, EMAIL))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.EMAIL_VERIFICATION_REQUIRED);
    }
}