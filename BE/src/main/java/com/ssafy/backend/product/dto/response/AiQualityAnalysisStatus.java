package com.ssafy.backend.product.dto.response;

/**
 * 상품 상세 "AI 분석" 탭의 상태(019-product-quality-multi-image.md). FE 원 스펙은
 * {@code ANALYZING}/{@code FAILED}까지 5종이지만, 이 값은 BE가 만드는 게 아니라 FE가 AI job을
 * 직접 폴링해 얻은 결과를 등록 시점에 넘겨받아 저장한 것뿐이라(041-quality-inspection-
 * integration.md §1) 그 두 상태는 BE 쪽에서 존재할 수 없다 — 여기 있는 3종만 나온다.
 */
public enum AiQualityAnalysisStatus {
    /** aiQualityFindings 자체를 등록 시점에 받지 않았다. */
    NOT_REQUESTED,
    /** 요청은 받았으나 인정된 하자가 0건. */
    NO_FINDINGS,
    /** 1건 이상의 finding이 저장돼 있다. */
    COMPLETED
}
