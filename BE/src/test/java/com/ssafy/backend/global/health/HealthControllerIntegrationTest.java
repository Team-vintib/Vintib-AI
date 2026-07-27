package com.ssafy.backend.global.health;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.backend.global.client.AiClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * 개발 환경 배선 확인용 샘플 통합 테스트 (S15P11A108-294).
 *
 * 전체 애플리케이션 컨텍스트를 띄워 PostgreSQL·Redis 연결까지 포함해 검증한다.
 * CI(be-test)는 postgres:18-alpine / redis:8.8-alpine 을 services 로 붙여주므로
 * 운영과 동일한 DB 엔진으로 이 테스트가 돈다. 로컬 실행 시에는 레포 루트에서
 * `docker compose up -d postgres redis` 로 먼저 띄운다.
 *
 * MockMvc 는 {@code @AutoConfigureMockMvc} 대신 WebApplicationContext 에서 직접 구성한다
 * (Spring Boot 4 모듈러 테스트 스타터에는 해당 자동설정 애노테이션이 포함되지 않는다).
 * 외부 의존인 AI 서버는 {@link MockitoBean} 으로 대체해 네트워크 없이 결정적으로 검증한다.
 */
@SpringBootTest
class HealthControllerIntegrationTest {

    @Autowired
    private WebApplicationContext context;

    @MockitoBean
    private AiClient aiClient;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context).build();
    }

    @Test
    void health_returnsUp_whenAiReachable() throws Exception {
        given(aiClient.isHealthy()).willReturn(true);

        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.backend").value("UP"))
                .andExpect(jsonPath("$.data.aiServer").value("UP"))
                .andExpect(jsonPath("$.error").doesNotExist());
    }

    @Test
    void health_reportsAiDown_butBackendUp_whenAiUnreachable() throws Exception {
        // AI 서버가 죽어도 백엔드는 UP 을 반환해야 한다.
        given(aiClient.isHealthy()).willReturn(false);

        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.backend").value("UP"))
                .andExpect(jsonPath("$.data.aiServer").value("DOWN"));
    }
}