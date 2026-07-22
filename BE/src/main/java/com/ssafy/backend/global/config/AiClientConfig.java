package com.ssafy.backend.global.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Spring → FastAPI 호출 설정.
 * Spring 은 FastAPI 게이트웨이만 바라본다. 추론용 노트북 연결은 AI 팀 영역이다.
 */
@Configuration
@EnableConfigurationProperties(AiClientConfig.AiProperties.class)
public class AiClientConfig {

    @ConfigurationProperties(prefix = "ai")
    public record AiProperties(String baseUrl, Duration connectTimeout, Duration readTimeout) {
    }

    @Bean
    public RestClient aiRestClient(AiProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.connectTimeout());
        factory.setReadTimeout(properties.readTimeout());

        return RestClient.builder()
                .baseUrl(properties.baseUrl())
                .requestFactory(factory)
                .build();
    }
}
