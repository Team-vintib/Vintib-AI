package com.ssafy.backend.global.health;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.response.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 개발 환경 배선 확인용 엔드포인트.
 * PostgreSQL·Redis 상태는 actuator 가 자동으로 잡아주므로 여기서는 FastAPI 도달 여부만 본다.
 */
@RestController
@RequestMapping("/api/health")
public class HealthController {

    private final AiClient aiClient;

    public HealthController(AiClient aiClient) {
        this.aiClient = aiClient;
    }

    @GetMapping
    public ApiResponse<HealthResponse> health() {
        return ApiResponse.success(new HealthResponse("UP", aiClient.isHealthy() ? "UP" : "DOWN"));
    }

    public record HealthResponse(String backend, String aiServer) {
    }
}