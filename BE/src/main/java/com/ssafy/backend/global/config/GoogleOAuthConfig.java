package com.ssafy.backend.global.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/** 구글 로그인(SY039, SSAFY SSO 대체) 연동용 {@link RestClient}. 인증은 헤더가 아니라 요청 파라미터로 하므로 기본 헤더가 필요 없다. */
@Configuration
@EnableConfigurationProperties(GoogleOAuthConfig.GoogleOAuthProperties.class)
public class GoogleOAuthConfig {

    @ConfigurationProperties(prefix = "google-oauth")
    public record GoogleOAuthProperties(
            String baseUrl, String clientId, String clientSecret,
            Duration connectTimeout, Duration readTimeout) {
    }

    @Bean
    public RestClient googleOAuthRestClient(GoogleOAuthProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.connectTimeout());
        factory.setReadTimeout(properties.readTimeout());

        return RestClient.builder()
                .baseUrl(properties.baseUrl())
                .requestFactory(factory)
                .build();
    }
}
