package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

public record AiQualityAnalysisImageResponse(
        @Schema(example = "앞면") String label,
        @Schema(example = "https://.../products/1/front.jpg") String originalImageUrl,
        @Schema(
                description = "AI 주석(빨간 네모) 이미지. 등록 흐름에서는 별도 주석 이미지를 만들지 않아"
                        + " originalImageUrl과 항상 같다 — FE가 findings[].box로 오버레이한다.",
                example = "https://.../products/1/front.jpg")
                String analyzedImageUrl,
        @Schema(description = "이 사진에 대한 AI 한 줄 요약(원본 image_summaries 그대로, CH002)")
                String summary,
        List<AiQualityFindingResponse> findings) {
}
