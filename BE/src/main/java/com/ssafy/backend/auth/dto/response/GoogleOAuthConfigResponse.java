package com.ssafy.backend.auth.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;

/** 구글 로그인 client_id 공개 조회. 비밀값이 아니므로 그대로 내려준다. */
public record GoogleOAuthConfigResponse(

        @Schema(example = "619045958877-k6kvnr8if7ra80iib5c2rkstmlbb4hk8.apps.googleusercontent.com")
        String clientId
) {
}
