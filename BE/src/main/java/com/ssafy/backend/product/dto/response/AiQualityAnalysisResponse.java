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

    // CH002부터 원본(quality_inspection_result)에서 직접 조립하면서 Product.qualityInspectionStatus를
    // 그대로 쓸 수 있게 됐다 — 예전엔 finding row 유무로만 상태를 추측해서 ANALYZING/FAILED를 BE가
    // 만들 수 없었는데(SY043), 이제 job 상태를 그대로 반영한다.
    public static AiQualityAnalysisResponse analyzing() {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.ANALYZING, List.of(), DISCLAIMER);
    }

    public static AiQualityAnalysisResponse failed() {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.FAILED, List.of(), DISCLAIMER);
    }

    public static AiQualityAnalysisResponse noFindings() {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.NO_FINDINGS, List.of(), DISCLAIMER);
    }

    public static AiQualityAnalysisResponse completed(List<AiQualityAnalysisImageResponse> images) {
        return new AiQualityAnalysisResponse(AiQualityAnalysisStatus.COMPLETED, images, DISCLAIMER);
    }
}
