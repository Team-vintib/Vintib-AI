# 데이터 사전 (S15P11A108-52)

> ⚠️ **이 파일은 자동 생성됩니다. 직접 고치지 마세요.**
> 재생성: `bash BE/docs/db/regen.sh` — 다음 실행 때 수정분이 덮어써집니다.
>
> | 바꾸고 싶은 것 | 고칠 파일 |
> | --- | --- |
> | 컬럼·타입·제약·기본값 | [`schema.sql`](./schema.sql) |
> | 설명 문구 | [`comments.sql`](./comments.sql) |
> | 표 형식·항목 구성 | [`gen-data-dictionary.sql`](./gen-data-dictionary.sql) |

대상 DB: **PostgreSQL 18** · 관련 문서: [ERD 및 상태 설계](./erd.md)

## 이 문서를 손으로 쓰지 않은 이유

데이터 사전을 사람이 옮겨 적으면 스키마가 바뀔 때 **조용히 어긋난다.** 컬럼 하나가 추가돼도 문서는 그대로 남고, 그걸 알아채는 시점은 보통 그 문서를 믿고 코드를 짠 뒤다.

그래서 구조(컬럼·타입·NULL·기본값·키·CHECK·인덱스)는 `schema.sql`을 적용한 실제 DB의 시스템 카탈로그에서 읽어오고, 설명은 `COMMENT ON`으로 DB에 심어 함께 읽어온다. 문서와 DDL이 갈라질 수 없는 구조다.

부수 효과로 `psql \d+`, DataGrip, DBeaver에서도 같은 설명이 보인다.

## 읽는 법

- **키** — `PK` / `FK→대상테이블` / `UQ`(유니크 제약)
- **CHECK 제약** — 상태 enum과 업무 규칙이 여기 들어 있다. 애플리케이션 검증이 뚫려도 DB가 막는 지점이다
- **인덱스** — `ux_` 접두어는 유니크. 특히 `WHERE` 절이 붙은 **부분 유니크 인덱스가 동시성 정책의 핵심**이다 (근거는 [`erd.md`](./erd.md) §4)

## 담당 경계

| 담당 | 테이블 |
| --- | --- |
| **서윤** | `member*`, `business_info`, `brand`, `category`, `product*`, `wish`, `follow`, `point_*`, `orders`, `order_shipment`, `notification` |
| **정윤** | `live`, `live_product`, `auction`, `bid`, `chat_message` |

---

## 테이블 목록
