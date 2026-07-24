package com.ssafy.backend.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * ⚠️ 임시 스텁. 현재는 모든 요청을 허용한다.
 *
 * spring-boot-starter-security 가 있는 상태에서 설정이 없으면 기본 HTTP Basic 이 걸려
 * 헬스체크·Swagger 를 포함한 모든 요청이 401 이 된다. 개발 환경을 띄우기 위한 최소 설정이다.
 *
 * 실제 인증/인가(JWT 필터, 엔드포인트별 권한)는 서윤의 AUTH-002(-220) 토큰 발급이 나온 뒤
 * 이 클래스에 얹는다. 그 전까지 여기에 도메인 권한 규칙을 추가하지 말 것.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .httpBasic(basic -> basic.disable())
                .formLogin(form -> form.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
                .cors(Customizer.withDefaults())
                .build();
    }
}