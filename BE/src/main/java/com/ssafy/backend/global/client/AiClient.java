package com.ssafy.backend.global.client;

import com.ssafy.backend.global.client.dto.AiJobCreatedResponse;
import com.ssafy.backend.global.client.dto.AiJobResponse;
import com.ssafy.backend.global.client.dto.RegistrationModelCutJobRequest;
import com.ssafy.backend.global.client.dto.TryOnJobRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * FastAPI AI 게이트웨이 호출 클라이언트. job 생성·폴링 엔드포인트는 워커 전용이 아니라
 * BE가 호출하는 쪽이라 인증 헤더가 필요 없다(`AI/docs/infra-architecture.md` §3.2,
 * `docs/requests/BE/040-tryon-job-contract.md`).
 */
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

    /** {@code POST /ai/tryon} — 핵심 AI 시착 job 생성. */
    public String createTryOnJob(TryOnJobRequest request) {
        AiJobCreatedResponse response = aiRestClient.post()
                .uri("/ai/tryon")
                .body(request)
                .retrieve()
                .body(AiJobCreatedResponse.class);
        return response.jobId();
    }

    /** {@code POST /ai/tryon/registration-model-cut} — 등록 시 AI 착용컷 job 생성. */
    public String createRegistrationModelCutJob(String productImageUrl, String gender, String maskType) {
        AiJobCreatedResponse response = aiRestClient.post()
                .uri("/ai/tryon/registration-model-cut")
                .body(new RegistrationModelCutJobRequest(productImageUrl, gender, maskType))
                .retrieve()
                .body(AiJobCreatedResponse.class);
        return response.jobId();
    }

    /** {@code GET /ai/jobs/{jobId}} — 모든 AI 기능이 공유하는 공통 job 상태 조회. */
    public AiJobResponse getJob(String jobId) {
        return aiRestClient.get()
                .uri("/ai/jobs/{jobId}", jobId)
                .retrieve()
                .body(AiJobResponse.class);
    }
}
