package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * {@code POST /ai/tryon} job payload. 필드명은 AI 쪽 계약(`docs/requests/BE/
 * 040-tryon-job-contract.md`, {@code worker/tryon_worker_example.py}의
 * {@code run_inference()} 독스트링)을 그대로 따른다 — snake_case로 직렬화해야 한다.
 */
public record TryOnJobRequest(
        @JsonProperty("user_image_url") String userImageUrl,
        @JsonProperty("product_image_url") String productImageUrl,
        @JsonProperty("mask_type") String maskType,
        @JsonProperty("fit_type") String fitType,
        @JsonProperty("body_height_cm") Double bodyHeightCm,
        @JsonProperty("body_weight_kg") Double bodyWeightKg,
        @JsonProperty("body_waist_cm") Double bodyWaistCm,
        @JsonProperty("garment_measurements") Map<String, Double> garmentMeasurements) {
}
