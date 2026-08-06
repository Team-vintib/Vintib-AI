package com.ssafy.backend.global.client;

/** 검증된 구글 사용자 정보(GoogleOAuthClient#verifyIdToken 반환값). */
public record GoogleIdentity(String googleId, String email, String name, String pictureUrl) {
}
