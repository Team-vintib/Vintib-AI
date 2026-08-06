package com.ssafy.backend.global.client;

import com.ssafy.backend.global.config.GoogleOAuthConfig.GoogleOAuthProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 구글 로그인 연동(SY039, SSAFY SSO 대체). Authorization Code를 시크릿으로 직접 교환하고,
 * tokeninfo 엔드포인트로 id_token을 검증한다(별도 JWT/JWKS 라이브러리 없이 기존 클라이언트
 * 패턴만으로 처리 — TossPaymentsClient와 같은 이유로 실패를 삼키지 않고 그대로 전파한다).
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GoogleOAuthClient {

    private final RestClient googleOAuthRestClient;
    private final GoogleOAuthProperties properties;

    public String exchangeCode(String code, String redirectUri) {
        try {
            GoogleTokenResponse response = googleOAuthRestClient.post()
                    .uri("/token")
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(tokenRequestBody(code, redirectUri))
                    .retrieve()
                    .body(GoogleTokenResponse.class);
            if (response == null || response.idToken() == null) {
                throw new CustomException(ErrorCode.GOOGLE_AUTH_FAILED);
            }
            return response.idToken();
        } catch (RestClientException e) {
            log.warn("구글 토큰 교환 실패: {}", e.getMessage());
            throw new CustomException(ErrorCode.GOOGLE_AUTH_FAILED);
        }
    }

    public GoogleIdentity verifyIdToken(String idToken) {
        try {
            GoogleTokenInfoResponse info = googleOAuthRestClient.get()
                    .uri(uriBuilder -> uriBuilder.path("/tokeninfo").queryParam("id_token", idToken).build())
                    .retrieve()
                    .body(GoogleTokenInfoResponse.class);
            if (info == null || info.sub() == null || info.email() == null
                    || !properties.clientId().equals(info.aud())) {
                throw new CustomException(ErrorCode.GOOGLE_AUTH_FAILED);
            }
            return new GoogleIdentity(info.sub(), info.email(), info.name(), info.picture());
        } catch (RestClientException e) {
            log.warn("구글 id_token 검증 실패: {}", e.getMessage());
            throw new CustomException(ErrorCode.GOOGLE_AUTH_FAILED);
        }
    }

    private MultiValueMap<String, String> tokenRequestBody(String code, String redirectUri) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("code", code);
        form.add("client_id", properties.clientId());
        form.add("client_secret", properties.clientSecret());
        form.add("redirect_uri", redirectUri);
        form.add("grant_type", "authorization_code");
        return form;
    }
}
