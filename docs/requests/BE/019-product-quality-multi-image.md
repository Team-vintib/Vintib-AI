# 019 상품 상세 — AI 품질 검수(다중 이미지) 데이터 요청

**요청자 파트**: FE
**대상 파트**: BE (+ AI 분석 결과 제공 필요)

## 배경/이유
상품 상세의 "AI 분석" 패널(`AiQualityAnalysisPanel`)이 지금까지 **검수 이미지 1장(원본↔검수 1쌍)** 만 표시하도록 되어 있었다. 실제로는 **검수 이미지가 여러 장 들어올 수 있어야** 하고(필수 2장: 앞/뒤, 상한 없음), 상세 페이지에서 **밑으로 쭉 쌓지 않고 넘겨(caroulsel) 가며** 확인해야 한다(세로로 다 쌓으면 페이지가 너무 길어짐).

FE는 이미 **다중 이미지 + 넘겨보기 + 이미지별 설명 전환** UI를 구현했고, 넘길 때마다 아래 설명·findings가 그 이미지 것으로 바뀐다. 다만 **실제 AI 검수 데이터 계약이 없어** 현재는 상품 이미지를 재사용한 **데모용 mock**(`aiQualityAnalysisMockData.ts`, "Mock 전용" 표시)으로 동작한다. BE/AI 데이터가 내려오면 mock을 제거하고 매핑으로 교체한다.

## 요청 내용
상품 상세 응답 `GET /api/products/{id}`에 **AI 품질 검수 결과를 이미지 배열 형태**로 포함해 달라(또는 별도 엔드포인트 — 방식은 BE 판단). 내용(원본/검수 이미지, 탐지 위치, 설명)은 **AI 분석 파트가 생성**하고 BE가 상세 응답에 실어 준다.

FE가 필요한 형태(현재 뷰모델 `AiQualityAnalysis` 기준):
```jsonc
"aiQualityAnalysis": {
  "status": "COMPLETED",           // NOT_REQUESTED | ANALYZING | COMPLETED | NO_FINDINGS | FAILED
  "images": [                       // 검수 이미지 여러 장 (필수 2장 앞/뒤, 상한 없음)
    {
      "label": "앞면",             // 이미지 구분 라벨
      "originalImageUrl": "https://.../front.jpg",
      "analyzedImageUrl": "https://.../front-analyzed.jpg", // AI 주석 이미지(없으면 원본과 동일 URL + 아래 box로 표시)
      "summary": "앞면 상태 요약 …",
      "findings": [
        {
          "type": "보풀",
          "location": "가슴 중앙",
          "description": "…",
          "box": { "x": 42, "y": 28, "width": 18, "height": 15 } // 검수 이미지 위 탐지 위치(프레임 기준 %, 0~100). 없으면 생략 가능
        }
      ]
    }
  ],
  "disclaimer": "AI 분석 결과는 참고용입니다 …"
}
```

- **`images`가 핵심**: 이미지별로 `originalImageUrl`·`analyzedImageUrl`·`summary`·`findings`를 각각 가진다(넘기면 설명도 함께 전환).
- `analyzedImageUrl`에 **빨간 네모가 그려진 주석 이미지**를 주면 그대로 표시한다. 주석 이미지가 없다면 `analyzedImageUrl`을 원본과 동일하게 주고 `findings[].box`(%) 좌표만 주면 **FE가 원본 위에 빨간 네모를 오버레이**한다. 둘 중 편한 방식으로.
- `status`가 `COMPLETED`이고 `images`가 있을 때만 캐러셀을 렌더한다. 그 외 상태는 안내 문구로 처리(기존 동작 유지).
- 개수 상한은 없음(필수 2장). `findings`는 이미지당 0개 이상.

## 일정
- FE는 다중 이미지 캐러셀 구현 완료(현재 mock). **BE/AI 데이터가 상세 응답에 담기는 시점부터** mock 제거 + 매핑 연결(추가 FE 작업 소량).

## 관련 자료
- FE: `FE/src/domains/product/components/AiQualityAnalysisPanel.vue`, `FE/src/domains/product/api/productApi.ts`(`toProductDetailViewData` → 현재 `buildMockAiQualityAnalysis`), 타입 `AiQualityAnalysis` / `AiQualityAnalysisImage` / `AiQualityFinding(box)` (`productDetail.types.ts`)
- Mock(교체 대상): `FE/src/domains/product/constants/aiQualityAnalysisMockData.ts`
- 기능: 상품 상세 AI 검수 이미지 넘겨보기

## 처리 결과
(BE 반영 후 기입)
