package com.ssafy.backend.global.client;

import com.fasterxml.jackson.annotation.JsonProperty;

/** 구글 토큰 교환 응답(POST /token) 중 필요한 필드만 담는다. */
public record GoogleTokenResponse(@JsonProperty("id_token") String idToken) {
}
