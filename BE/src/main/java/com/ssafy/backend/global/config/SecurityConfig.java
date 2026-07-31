package com.ssafy.backend.global.config;

import com.ssafy.backend.auth.jwt.JwtAuthenticationEntryPoint;
import com.ssafy.backend.auth.jwt.JwtAuthenticationFilter;
import com.ssafy.backend.auth.jwt.OnboardingRequiredFilter;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

/**
 * 인증이 필요 없는 엔드포인트만 permitAll, 나머지는 JwtAuthenticationFilter가 채운
 * SecurityContext 인증 정보를 요구한다.
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private static final String[] PUBLIC_ENDPOINTS = {
            "/api/auth/signup",
            "/api/auth/signin",
            "/api/auth/reissue",
            "/api/auth/email/**",
            "/api/health",
            // 홈 콘텐츠 조회는 비회원도 가능(HOME-001). 정확 경로만 열어 /api/home/following(HOME-002)은 인증 필요로 남긴다.
            "/api/home",
            // 카테고리/브랜드 마스터 조회는 비회원도 가능(SY007)
            "/api/categories",
            "/api/brands",
            // STOMP 핸드셰이크는 비회원도 통과해야 한다(라이브 시청·채팅 읽기). 인증은 여기서
            // 하지 않고 CONNECT 프레임에서 StompAuthChannelInterceptor 가 처리한다 — 브라우저는
            // 핸드셰이크 요청에 Authorization 헤더를 붙일 수 없다.
            "/ws/**",
            "/actuator/**",
            "/swagger-ui/**",
            "/v3/api-docs/**"
    };

    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final OnboardingRequiredFilter onboardingRequiredFilter;
    private final JwtAuthenticationEntryPoint jwtAuthenticationEntryPoint;

    @Value("${cors.allowed-origins}")
    private List<String> corsAllowedOrigins;

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(corsAllowedOrigins);
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .httpBasic(basic -> basic.disable())
                .formLogin(form -> form.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_ENDPOINTS).permitAll()
                        // 상품 상세 조회(PROD-006)는 비회원도 가능. POST /api/products(등록)는 인증 필요로 남긴다.
                        .requestMatchers(HttpMethod.GET, "/api/products/{id}").permitAll()
                        // 라이브 목록·시청 조회(LIVE-005)는 비회원도 가능. 개설·상태 전이는 인증 필요로 남긴다.
                        .requestMatchers(HttpMethod.GET, "/api/lives").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/lives/{liveId}").permitAll()
                        // 채팅 이력 조회(CHAT-001)도 비회원 공개. 시청이 열려 있으니 대화 읽기도
                        // 열어야 한다. 발언은 STOMP 쪽에서 principal 유무로 막는다.
                        .requestMatchers(HttpMethod.GET, "/api/lives/{liveId}/chat-messages").permitAll()
                        // 영상 접속 토큰도 비회원 발급 대상이다. 시청이 열려 있으니 영상도 열어야 한다.
                        // 발행 권한은 토큰 안에서 갈린다 — 호스트 본인일 때만 송출이 허용된다.
                        .requestMatchers(HttpMethod.POST, "/api/lives/{liveId}/video-token").permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex.authenticationEntryPoint(jwtAuthenticationEntryPoint))
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
                .addFilterAfter(onboardingRequiredFilter, JwtAuthenticationFilter.class)
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .build();
    }
}