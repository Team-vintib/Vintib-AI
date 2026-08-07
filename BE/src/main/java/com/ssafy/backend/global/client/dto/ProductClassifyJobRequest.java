package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * {@code POST /product-classifier/classify} job payload. 상품 생성 전(사전업로드) 트리거라
 * {@code product_id}는 보내지 않는다 — AI 쪽 스키마도 optional이라 생략하면 {@code null}로
 * 처리된다(`docs/requests/BE/045-classify-pre-upload-integration.md`).
 */
public record ProductClassifyJobRequest(@JsonProperty("image_url") String imageUrl) {
}
