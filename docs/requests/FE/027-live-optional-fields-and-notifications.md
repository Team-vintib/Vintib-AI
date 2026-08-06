# 027 라이브 시청 상품 선택 필드 3종 — 남은 FE 항목

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-04
- **원 요청**: `docs/requests/BE/003-live-tryon-contract.md` §3.5(선택 필드)

> §2 알림 2종(`LIVE_STARTED`/`AUCTION_OUTBID`)은 BE에서 실제로 생성되며 표시는 알림 도메인 몫이라 덜어냈다.
> §3 미낙찰 예비답변·§4 경매 종료(→`030`)는 반영 완료. 아래 §1(선택 필드 바인딩)만 남는다.

## 남은 항목 — `LiveProductResponse` 선택 필드 3종 바인딩 (미반영)

`FE/src/domains/live/api/liveWatchApi.ts`의 `mapLiveProductDto`가 아직 세 필드를 `null`로 하드코딩하고
"`LiveProductResponse`에 없음"이라는 **지금은 틀린** 주석을 달아 두었다. 셋 다 이제 내려온다 —
`dto.material`·`dto.measurements`·`dto.defectSummary`를 그대로 매핑하면 시청 화면에서 소재·실측·하자
요약이 바로 보인다(뷰모델 타입 `LiveWatchProduct`에는 이미 필드가 있음. 단 `measurements`는 뷰모델이
`string | null`이라 객체 → 표시 문자열 변환이 필요).

```jsonc
{
  "material": "코튼 100%",                          // 없으면 null
  "measurements": { "어깨너비": 45, "총장": 70 },     // 없으면 null
  "defectSummary": "밑단 오염, 우측 소매 실밥 풀림"    // 한 줄 요약(목록 아님). 상세 목록은 GET /api/products/{id}의 defects[]
}
```

- `material`/`measurements`는 상품 등록 시 입력한 값을 그대로 내림.
- 편성 상품 수만큼 상세를 더 읽지 않고 시청 화면 상품 목록 조회 한 번에 같이 온다.
