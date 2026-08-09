package com.ssafy.backend.product.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.Map;

/**
 * AI 원본 검수 결과({@code quality_inspection_result})의 finding 하나를 그대로 옮긴 것(CH002).
 *
 * <p>별도 저장 테이블 없이 매 조회마다
 * {@link com.ssafy.backend.product.entity.Product#getQualityInspectionResult()} 원본에서
 * 조립한다 — {@code isExcluded}만 {@code Product.excludedQualityFindingKeys}를 대조해서 얹는다.
 * 원본을 축소 저장하던 이전 방식(SY043 §2)은 이걸로 대체됐다.
 */
public record AiQualityFindingResponse(
        @Schema(description = "finding 고정 식별자(제외 처리 앵커)", example = "hole_tear_0_9_1") String key,
        @Schema(description = "하자 유형 한글 라벨(AI 원본 label 그대로)", example = "구멍·찢어짐") String type,
        @Schema(description = "AI 원본 부위 코드 그대로(번역 안 함 — FE가 aiSectionLabels로 매핑)", example = "HEM_RIGHT")
                String location,
        @Schema(description = "AI 한 줄 설명. SUSPECTED 등 상황에 따라 null일 수 있다", example = "구멍이 생긴 부분이 확인됩니다.")
                String description,
        @Schema(description = "이 사진 안에서의 표시 번호(1부터) — 등록 화면 넘버링과 동일") Integer no,
        @Schema(description = "검수 이미지 위 탐지 위치(프레임 기준 %, 0~100, 반올림 없음)") Box box,
        @Schema(description = "판매자가 \"하자 아님\"으로 표시했는지") boolean isExcluded) {

    public record Box(double x, double y, double width, double height) {
    }

    /**
     * AI 원본 finding(raw JSON map) + 제외 여부로 조립한다.
     *
     * <p>{@code bbox}는 AI가 주는 정규화 xyxy([x1,y1,x2,y2], 0~1)를 프레임 기준 %
     * {@code {x,y,width,height}}로 변환한다(반올림하지 않음 — FE
     * {@code qualityFindingBox.ts::toPercentBox()}와 동일한 공식이라 등록 화면과 픽셀 단위로
     * 같은 결과가 나온다).
     */
    @SuppressWarnings("unchecked")
    public static AiQualityFindingResponse from(Map<String, Object> finding, boolean excluded) {
        return new AiQualityFindingResponse(
                (String) finding.get("key"),
                (String) finding.get("label"),
                (String) finding.get("section"),
                (String) finding.get("description"),
                asInteger(finding.get("no")),
                toBox((List<Number>) finding.get("bbox")),
                excluded);
    }

    private static Integer asInteger(Object value) {
        return value instanceof Number number ? number.intValue() : null;
    }

    private static Box toBox(List<Number> bbox) {
        if (bbox == null || bbox.size() < 4) {
            return null;
        }
        double x1 = bbox.get(0).doubleValue();
        double y1 = bbox.get(1).doubleValue();
        double x2 = bbox.get(2).doubleValue();
        double y2 = bbox.get(3).doubleValue();
        return new Box(x1 * 100, y1 * 100, (x2 - x1) * 100, (y2 - y1) * 100);
    }
}
