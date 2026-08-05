package com.ssafy.backend.global.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * springdoc-openapi 설정. API 문서의 기본 메타데이터(제목·설명·버전)를 정의한다.
 * swagger-ui 노출 여부는 프로파일로 제어한다(application-*.yml).
 */
@Configuration
public class SwaggerConfig {

    // OpenAPI 스펙상 components 하위 키(securitySchemes 포함)는 ^[a-zA-Z0-9._-]+$ 만 허용되므로
    // 한글은 쓸 수 없다 — 사람이 보는 이름은 SecurityScheme.description()에 한글로 넣는다.
    private static final String BEARER_SCHEME_NAME = "bearerAuth";

    @Bean
    public OpenAPI vintibOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("VinTib API")
                        .description("빈티지·세컨핸드 의류 라이브 경매 플랫폼 백엔드 API")
                        .version("v0.1"))
                // swagger-ui 우측 상단 "Authorize" 버튼. 로그인/재발급 응답의 accessToken을
                // "Bearer " 접두어 없이 그대로 붙여넣으면 이후 모든 요청에 Authorization 헤더가 실린다.
                .addSecurityItem(new SecurityRequirement().addList(BEARER_SCHEME_NAME))
                .components(new Components()
                        .addSecuritySchemes(
                                BEARER_SCHEME_NAME,
                                new SecurityScheme()
                                        .type(SecurityScheme.Type.HTTP)
                                        .scheme("bearer")
                                        .bearerFormat("JWT")
                                        .description("JWT 인증 — 로그인/재발급 응답의 accessToken을 붙여넣는다.")));
    }
}