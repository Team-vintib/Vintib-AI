package com.ssafy.backend.auth.controller;

import com.ssafy.backend.auth.dto.request.EmailCodeVerifyRequest;
import com.ssafy.backend.auth.dto.request.EmailVerificationRequest;
import com.ssafy.backend.auth.dto.request.SignUpRequest;
import com.ssafy.backend.auth.dto.response.EmailVerificationTokenResponse;
import com.ssafy.backend.auth.dto.response.SignUpResponse;
import com.ssafy.backend.auth.service.AuthService;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "인증/회원", description = "회원가입 및 이메일 인증 API")
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "이메일 인증코드 발송", description = "입력한 이메일로 6자리 인증코드를 발송한다. 이미 가입된 이메일이면 거절한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "발송 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 가입된 이메일"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "429", description = "재발송 요청이 너무 잦음")
    })
    @PostMapping("/email/send-code")
    public ResponseEntity<ApiResponse<Void>> sendEmailVerificationCode(
            @Valid @RequestBody EmailVerificationRequest request) {
        authService.sendEmailVerificationCode(request.email());
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @Operation(summary = "이메일 인증코드 확인", description = "이메일과 인증코드가 일치하면 회원가입에 사용할 인증 토큰을 발급한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "인증 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "인증코드 불일치/만료 또는 시도 횟수 초과")
    })
    @PostMapping("/email/verify-code")
    public ResponseEntity<ApiResponse<EmailVerificationTokenResponse>> verifyEmailCode(
            @Valid @RequestBody EmailCodeVerifyRequest request) {
        String token = authService.verifyEmailCode(request.email(), request.code());
        return ResponseEntity.ok(ApiResponse.success(new EmailVerificationTokenResponse(token)));
    }

    @Operation(summary = "회원가입", description = "이메일 인증 토큰을 검증한 뒤 이메일/비밀번호/이름으로 회원가입을 완료한다.")
    @ApiResponses({
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "가입 성공"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "이메일 인증이 필요함(토큰 없음/불일치/만료)"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 가입된 이메일")
    })
    @PostMapping("/signup")
    public ResponseEntity<ApiResponse<SignUpResponse>> signUp(@Valid @RequestBody SignUpRequest request) {
        SignUpResponse response = authService.signUp(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }
}