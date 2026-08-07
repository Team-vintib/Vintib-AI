package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

public record AiQualityAnalysisResponse(
        AiQualityAnalysisStatus status,
        @Schema(description = "status=COMPLETED일 때만 값이 있다(앞/뒤 중 실제로 finding이 있는 사진만)")
                List<AiQualityAnalysisImageResponse> images,
        @Schema(example = "AI 분석 결과는 참고용입니다. 실제 상품 상태와 다를 수 있습니다.") String disclaimer) {

    private static final String DISCLAIMER = "AI 분석 결과는 참고용입니다. 실제 상품 상태와 다를 수 있습니다.";

    public static AiQualityAnalysisResponse notRequested() {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.NOT_REQUESTED, List.of(), DISCLAIMER);
    }

    public static AiQualityAnalysisResponse noFindings() {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.NO_FINDINGS, List.of(), DISCLAIMER);
    }

    public static AiQualityAnalysisResponse completed(List<AiQualityAnalysisImageResponse> images) {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.COMPLETED, images, DISCLAIMER);
    }
}
