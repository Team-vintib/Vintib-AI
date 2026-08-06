package com.ssafy.backend.global.client;

/** 구글 id_token 검증 응답(GET /tokeninfo) 중 필요한 필드만 담는다. */
public record GoogleTokenInfoResponse(String aud, String sub, String email, String name, String picture) {
}
