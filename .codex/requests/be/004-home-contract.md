# 004 Home API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 홈/팔로잉 홈 화면에서 사용하는 카드 필드와 남은 보강 항목을 정리한다.
- 우선순위: P1
- 시연 필수 여부: 홈 화면 시연은 현재 API로 가능. `hostId`와 노출 정책은 품질 보강 항목.

## 2. 현재 연동 상태

- 연동 완료 API
  - `GET /api/home`
  - `GET /api/home/following`
- FE 구현 완료 범위
  - 홈 섹션 렌더링
  - 라이브 카드 표시 및 라이브 상세 이동
  - 상품 카드 표시 및 상품 상세 이동
- 현재 임시 처리 또는 Mock 사용 여부
  - 화면 렌더링 자체는 실제 API 응답으로 가능하다.
  - 일부 프로필 이동용 id는 응답에 없으면 이동 기능을 제한하거나 숨겨야 한다.

## 3. 추가 구현 요청

### 3.1 라이브 카드 hostId 제공

- Method / Endpoint: `GET /api/home`, `GET /api/home/following`
- 요청 목적: 홈 라이브 카드에서 호스트/판매자 프로필 이동을 지원한다.
- FE 사용처: 홈 라이브 카드, 팔로잉 홈 라이브 카드
- 요청 데이터: 없음
- 응답 데이터
  - live card item에 `hostId`: number | null 추가
- 응답 예시

```json
{
  "success": true,
  "data": {
    "lives": [
      {
        "liveId": 1,
        "hostId": 10,
        "title": "빈티지 라이브",
        "hostNickname": "vintagelover",
        "thumbnailUrl": null,
        "broadcastStatus": "LIVE",
        "viewerCount": 120
      }
    ]
  },
  "error": null
}
```

### 3.2 홈 섹션 노출 정책 문서화

- Method / Endpoint: `GET /api/home`, `GET /api/home/following`
- 요청 목적: FE가 빈 섹션, 정렬 기준, 최대 노출 개수를 예측 가능하게 처리한다.
- FE 사용처: 홈 섹션 렌더링
- 요청 데이터: 없음
- 응답 데이터
  - 기존 응답 유지 가능
  - 문서로 섹션별 정렬 기준, 최대 노출 개수, 빈 섹션 포함 여부 명시 요청
- 응답 예시: 기존 응답 유지

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - live card item에 `hostId` 추가 요청
- 추가할 필드
  - `hostId`: number | null
- 변경 영향 범위
  - 홈 라이브 카드에서 호스트 프로필 이동
  - 공개 프로필 API 연결 시 진입점

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 홈 카드에서 호스트 프로필 이동
  - 개인화 정렬 고도화
- 추후 구현 예정 기능
  - 추천 사유 표시
  - 섹션별 더보기 API 분리

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 홈 섹션 정렬 기준
  - 섹션별 최대 노출 개수
  - 빈 섹션 노출 여부
  - 비회원 홈에서 `isWished`를 `false`로 줄지 `null`로 줄지
- 아직 확정되지 않은 응답 구조나 정책
  - 없음

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - `GET /api/home`
  - `GET /api/home/following`
- 기존 규격을 유지하면 되는 기능
  - Home 현재 화면 렌더링
  - product card 기본 표시 필드
