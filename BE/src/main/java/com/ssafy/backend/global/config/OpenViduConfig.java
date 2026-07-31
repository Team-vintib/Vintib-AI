package com.ssafy.backend.global.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * OpenVidu v3(LiveKit 기반) 접속 설정.
 *
 * <p><b>값이 없어도 애플리케이션은 뜬다.</b> 미디어 서버 구축(-448)은 별도 작업이고, 로컬 개발과
 * CI 에는 서버가 없다. 여기서 기동을 막으면 영상과 무관한 테스트까지 전부 깨진다. 설정이
 * 비어 있으면 {@code OpenViduClient} 가 스스로 "미구성"으로 판단해 토큰 발급만 거부한다.
 */
@Configuration
@EnableConfigurationProperties(OpenViduConfig.OpenViduProperties.class)
public class OpenViduConfig {

    /**
     * <b>{@code serverUrl} 과 {@code apiUrl} 은 서로 다른 주소다.</b> 하나로 합치면 배포 환경에서
     * 반드시 깨진다 — 브라우저는 외부에서 Caddy(443)를 거쳐 들어오고, 백엔드는 같은 도커
     * 네트워크 안에서 미디어 서버에 직접 붙는다. 백엔드가 외부 주소로 자기 자신을 한 바퀴 돌면
     * TLS·프록시를 불필요하게 타고, 반대로 브라우저에 내부 주소를 주면 아예 닿지 않는다.
     *
     * @param serverUrl 브라우저가 붙을 주소 (예: {@code wss://i15a108.p.ssafy.io}). 비면 미구성
     * @param apiUrl    백엔드가 room 관리 API 를 호출할 주소 (예: {@code http://livekit:7880}).
     *                  비어 있으면 {@code serverUrl} 을 그대로 쓴다 — 로컬에서 둘이 같은 경우
     * @param apiKey    LiveKit API key. 토큰 서명의 {@code iss} 가 된다
     * @param apiSecret LiveKit API secret. 토큰 서명 키
     * @param tokenTtl  발급 토큰 수명. 방송이 더 길어지면 FE 가 재발급받는다
     */
    @ConfigurationProperties(prefix = "openvidu")
    public record OpenViduProperties(
            String serverUrl, String apiUrl, String apiKey, String apiSecret, Duration tokenTtl) {

        public boolean isConfigured() {
            return hasText(serverUrl) && hasText(apiKey) && hasText(apiSecret);
        }

        /** room 관리 API 주소. 따로 주지 않았으면 브라우저용 주소를 그대로 쓴다. */
        public String resolvedApiUrl() {
            return hasText(apiUrl) ? apiUrl : serverUrl;
        }

        private static boolean hasText(String value) {
            return value != null && !value.isBlank();
        }
    }
}
