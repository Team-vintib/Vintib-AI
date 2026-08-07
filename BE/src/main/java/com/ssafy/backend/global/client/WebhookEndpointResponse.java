package com.ssafy.backend.global.client;

/** 웹훅 엔드포인트 등록 응답(POST /v1/webhooks/endpoints) 중 필요한 필드만 담는다. */
public record WebhookEndpointResponse(String endpointId) {
}