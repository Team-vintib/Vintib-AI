package com.ssafy.backend.global.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/** 택배 배송 조회(deliveryapi.co.kr, SHIP-002) 연동용 {@link RestClient}. */
@Configuration
@EnableConfigurationProperties(DeliveryApiConfig.DeliveryApiProperties.class)
public class DeliveryApiConfig {

    @ConfigurationProperties(prefix = "delivery-api")
    public record DeliveryApiProperties(
            String baseUrl, String apiKey, String secretKey, String endpointId, String webhookSecret,
            Duration connectTimeout, Duration readTimeout) {

        public boolean isConfigured() {
            return !apiKey.isBlank() && !secretKey.isBlank() && !endpointId.isBlank();
        }
    }

    @Bean
    public RestClient deliveryApiRestClient(DeliveryApiProperties properties) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.connectTimeout());
        factory.setReadTimeout(properties.readTimeout());

        return RestClient.builder()
                .baseUrl(properties.baseUrl())
                .requestFactory(factory)
                .defaultHeader("Authorization", "Bearer " + properties.apiKey() + ":" + properties.secretKey())
                .build();
    }
}
