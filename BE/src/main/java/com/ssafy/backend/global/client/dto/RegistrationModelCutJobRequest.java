package com.ssafy.backend.global.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * {@code POST /ai/tryon/registration-model-cut} job payload
 * (`docs/requests/BE/039-registration-ai-model-tryon.md` §1).
 */
public record RegistrationModelCutJobRequest(
        @JsonProperty("product_image_url") String productImageUrl,
        String gender,
        @JsonProperty("mask_type") String maskType) {
}
