package com.ssafy.backend.global.health;

import com.ssafy.backend.global.client.AiClient;
import com.ssafy.backend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 개발 환경 배선 확인용 엔드포인트.
 * PostgreSQL·Redis 상태는 actuator 가 자동으로 잡아주므로 여기서는 FastAPI 도달 여부만 본다.
 */
@Tag(name = "시스템", description = "서버 상태 확인 API")
@RestController
@RequestMapping("/api/health")
public class HealthController {

    private final AiClient aiClient;

    public HealthController(AiClient aiClient) {
        this.aiClient = aiClient;
    }

    @Operation(summary = "헬스체크", description = "백엔드와 AI 서버(FastAPI) 도달 여부를 반환한다. AI 서버가 죽어도 백엔드는 UP 을 반환한다.")
    @ApiResponses(
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "상태 조회 성공")
    )
    @GetMapping
    public ApiResponse<HealthResponse> health() {
        return ApiResponse.success(new HealthResponse("UP", aiClient.isHealthy() ? "UP" : "DOWN"));
    }

    public record HealthResponse(
            @Schema(description = "백엔드 상태", example = "UP") String backend,
            @Schema(description = "AI 서버(FastAPI) 도달 여부", example = "UP") String aiServer
    ) {
    }
}