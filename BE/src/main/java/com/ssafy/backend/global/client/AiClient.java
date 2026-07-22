package com.ssafy.backend.global.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Slf4j
@Component
public class AiClient {

    private final RestClient aiRestClient;

    public AiClient(RestClient aiRestClient) {
        this.aiRestClient = aiRestClient;
    }

    /**
     * FastAPI 게이트웨이 도달 여부만 확인한다. AI 서버가 죽어도 백엔드는 계속 떠 있어야 하므로
     * 예외를 삼키고 false 를 돌려준다.
     */
    public boolean isHealthy() {
        try {
            aiRestClient.get()
                    .uri("/health")
                    .retrieve()
                    .toBodilessEntity();
            return true;
        } catch (RestClientException e) {
            log.warn("AI 서버 헬스체크 실패: {}", e.getMessage());
            return false;
        }
    }
}
