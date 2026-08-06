# 상품 등록 — "AI 착용컷" 실제 연동 예고 (희동이/도우너 모델)

- **요청자 파트**: AI
- **대상 파트**: FE
- **관련 티켓**: `S15P11A108-211` 에픽 하위, `S15P11A108-568`
- **상태**: 요청 — BE 연동이 먼저 필요해서, 지금 당장 착수하실 건 아니고 미리
  공유드립니다.

## 배경

`ProductRegistrationPage.vue`의 "AI 착용컷 설정" 섹션(`aiModelEnabled`/
`aiModelGender`)을 확인했습니다. 지금은 선택값이 제출 요청에서 빠지고 결과
이미지 개념도 없는데, AI 쪽 파이프라인은 이미 프로덕션에 있어서 BE 연동만
붙이면 실제로 동작하게 만들 수 있습니다(`docs/requests/BE/
039-registration-ai-model-tryon.md`로 BE에 요청 완료).

## 요청 내용 (BE 연동 완료 후 착수)

1. **제출 시 값 포함**: 지금은 `aiModelEnabled`/`aiModelGender`가 제출 페이로드에서
   빠지는데, BE가 이 두 값을 받는 필드를 만들면 그대로 포함해 보내주세요.
2. **생성 결과 표시**: AI 이미지 생성은 시간이 걸립니다(경험상 2~3분대 — VLM 캡션 →
   FLUX → CatVTON 순차 처리). 즉시 완료되지 않으므로 "생성 중" 상태를 보여주고,
   완료되면 이미지 URL을 받아 상품 상세 페이지 보조 이미지로 노출하는 흐름이
   필요합니다.
3. **실패 처리**: 생성 실패 시(워커 미가동, 이미지 다운로드 실패 등) 등록 자체는
   막지 않고 착용컷만 없는 채로 진행되게 해주세요 — 필수 기능이 아니라 보조
   기능입니다.

## API 명세 (BE에 제안한 계약 — `docs/requests/BE/039-registration-ai-model-tryon.md`)

BE 쪽에 아래 계약을 제안해뒀습니다. 최종 필드명은 BE 컨벤션에 따라 조정될 수 있으니,
실제 착수 시점에 BE 응답을 한 번 더 확인해 주세요.

#### 등록 요청 — 기존 `POST /products`

```json
{
  "...": "기존 필드",
  "aiModelEnabled": true,
  "aiModelGender": "MALE"
}
```

`aiModelGender`는 `"FEMALE"`(도우너) \| `"MALE"`(희동이) 중 하나이고,
`aiModelEnabled=true`일 때만 필수입니다.

#### 등록 응답에 포함될 상태

```json
{
  "aiModelCut": { "status": "PENDING", "imageUrl": null }
}
```

#### 상태/결과 폴링 — 신규 `GET /products/{productId}/ai-model-cut`

```json
{
  "success": true,
  "data": { "status": "PROCESSING", "imageUrl": null },
  "error": null
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | `"NONE"` \| `"PENDING"` \| `"PROCESSING"` \| `"COMPLETED"` \| `"FAILED"` | `NONE`=미사용(이 영역 자체를 숨기면 됩니다), `PENDING`/`PROCESSING`=생성 중 UI, `COMPLETED`=`imageUrl` 노출, `FAILED`=착용컷 없이 등록 정상 진행 |
| `imageUrl` | string \| null | `status="COMPLETED"`일 때만 존재 |

폴링 주기는 FE 재량입니다(BE 제안 참고치: 5초 간격, 최대 1~2분).

## 참고

- BE 쪽 요청(전체 흐름): `docs/requests/BE/039-registration-ai-model-tryon.md`
- 설계 문서: `docs/plans/AI/CH021-registration-ai-model-tryon.md`
- 현재 FE 코드: `FE/src/domains/product/pages/ProductRegistrationPage.vue`,
  `FE/src/domains/product/types/productRegistration.types.ts`
