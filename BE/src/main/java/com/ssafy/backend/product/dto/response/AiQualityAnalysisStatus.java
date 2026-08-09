package com.ssafy.backend.product.dto.response;

/**
 * 상품 상세 "AI 분석" 탭의 상태(019-product-quality-multi-image.md).
 *
 * <p>CH002부터 {@code Product.qualityInspectionStatus}(BE가 직접 폴링·갱신하는 job 상태)를
 * 그대로 매핑한다 — 이전엔 finding row 유무로만 추측해서 {@code ANALYZING}/{@code FAILED}를
 * BE가 만들 수 없었지만(041-quality-inspection-integration.md §1 당시 한계), 이제 5종 모두
 * 정확히 나온다.
 */
public enum AiQualityAnalysisStatus {
    /** 하자 검수 job 자체가 아직 없다(QualityInspectionStatus.NONE). */
    NOT_REQUESTED,
    /** 검수 job이 진행 중이다(PENDING/PROCESSING). */
    ANALYZING,
    /** 검수는 끝났으나 인정된 하자가 0건이다. */
    NO_FINDINGS,
    /** 검수가 끝났고 1건 이상의 finding이 있다. */
    COMPLETED,
    /** 검수 job이 실패했다. */
    FAILED
}
