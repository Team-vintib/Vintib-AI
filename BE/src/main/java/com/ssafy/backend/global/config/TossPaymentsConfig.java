package com.ssafy.backend.global.config;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/** 토스페이먼츠 결제위젯 연동용 {@link RestClient}(POINT-001). */
@Configuration
@EnableConfigurationProperties(TossPaymentsConfig.TossPaymentsProperties.class)
public class TossPaymentsConfig {

    @ConfigurationProperties(prefix = "toss-payments")
    public record TossPaymentsProperties(
            String baseUrl, String secretKey, String clientKey, Duration connectTimeout, Duration readTimeout) {
    }

    @Bean
    public RestClient tossPaymentsRestClient(TossPaymentsProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.connectTimeout());
        factory.setReadTimeout(properties.readTimeout());

        // 토스는 시크릿 키를 Basic Auth 사용자명으로, 비밀번호는 빈 문자열로 쓴다.
        String credentials = Base64.getEncoder()
                .encodeToString((properties.secretKey() + ":").getBytes(StandardCharsets.UTF_8));

        return RestClient.builder()
                .baseUrl(properties.baseUrl())
                .requestFactory(factory)
                .defaultHeader("Authorization", "Basic " + credentials)
                .build();
    }
}