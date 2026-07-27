package com.ssafy.backend.global.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * springdoc-openapi 설정. API 문서의 기본 메타데이터(제목·설명·버전)를 정의한다.
 * swagger-ui 노출 여부는 프로파일로 제어한다(application-*.yml).
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI vintibOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("VinTib API")
                        .description("빈티지·세컨핸드 의류 라이브 경매 플랫폼 백엔드 API")
                        .version("v0.1"));
    }
}