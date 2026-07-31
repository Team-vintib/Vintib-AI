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

### `auction`

상품 1건에 대한 경매. 한 라이브에서 동시에 RUNNING 인 경매는 항상 1개다 (LIVE-004).

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `live_id` | `bigint` | NOT NULL |  | FK→live | 대상 라이브. |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 대상 상품. |
| `start_price` | `bigint` | NOT NULL |  |  | 시작가(원) (AUCT-001). |
| `bid_unit` | `bigint` | NOT NULL |  |  | 증액 단위(원). 다음 입찰가 = 현재가 + 이 값 (AUCT-003). |
| `duration_seconds` | `integer` | NOT NULL |  |  | 경매 진행 시간(초) (AUCT-001). |
| `status` | `varchar(20)` | NOT NULL | `'READY'` |  | READY(설정 완료) \| RUNNING(진행 중) \| SUCCESS(낙찰) \| FAILED(미낙찰) \| CANCELED |
| `current_price` | `bigint` | NOT NULL | `0` |  | 현재가(원). bid 집계 대신 비정규화해 들고 있다 — AUCT-011 실시간 표시가 초당 수십 회 조회된다. |
| `top_bidder_id` | `bigint` |  |  | FK→member | 현재 최고 입찰자. 닉네임만 공개한다 (AUCT-011). |
| `started_at` | `timestamptz` |  |  |  | 경매 시작 시각 (AUCT-002 이벤트 발행 시점). |
| `scheduled_end_at` | `timestamptz` |  |  |  | 종료 예정 시각. 종료 3초 이하에 입찰이 들어오면 5초 연장되며 갱신된다 (AUCT-010). |
| `ended_at` | `timestamptz` |  |  |  | 경매 종료 시각. 연장이 반영된 실제 종료 시점. |
| `extension_count` | `smallint` | NOT NULL | `0` |  | 연장 횟수. 제한은 없으나 이상 동작 검증·통계용으로 센다. |
| `winner_id` | `bigint` |  |  | FK→member | 낙찰자 (AUCT-012). status=SUCCESS 면 반드시 존재한다. |
| `final_price` | `bigint` |  |  |  | 낙찰가(원). status=SUCCESS 면 반드시 존재한다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |

**CHECK 제약**

- `ck_auction_bid_unit` — `CHECK ((bid_unit > 0))`
- `ck_auction_start_price` — `CHECK ((start_price >= 0))`
- `ck_auction_status` — `CHECK (((status)::text = ANY ((ARRAY['READY'::character varying, 'RUNNING'::character varying, 'SUCCESS'::character varying, 'FAILED'::character varying, 'CANCELED'::character varying])::text[])))`
- `ck_auction_success_fields` — `CHECK ((((status)::text <> 'SUCCESS'::text) OR ((winner_id IS NOT NULL) AND (final_price IS NOT NULL))))`

**인덱스**

- `ix_auction_live` — `CREATE INDEX ix_auction_live ON public.auction USING btree (live_id, created_at DESC)`
- `ix_auction_status` — `CREATE INDEX ix_auction_status ON public.auction USING btree (status) WHERE ((status)::text = 'RUNNING'::text)`
- `ux_auction_live_running` — `CREATE UNIQUE INDEX ux_auction_live_running ON public.auction USING btree (live_id) WHERE ((status)::text = 'RUNNING'::text)`

---

### `bid`

입찰 내역. 낙찰 판정과 포인트 보류의 근거가 되는 원장.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `auction_id` | `bigint` | NOT NULL |  | FK→auction | 대상 경매. |
| `bidder_id` | `bigint` | NOT NULL |  | FK→member | 입찰자. |
| `bid_price` | `bigint` | NOT NULL |  |  | 입찰가(원). 같은 경매에서 동일 가격은 단 한 번만 성립한다. |
| `status` | `varchar(20)` | NOT NULL | `'ACTIVE'` |  | ACTIVE(현재 최고) \| OUTBID(상위 입찰에 밀림) \| WON(낙찰) \| LOST(종료 시점 최고가 아님) |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | ⭐ 서버 수신 시각. 선착순 판정의 유일한 기준이며 클라이언트 클릭 시각은 쓰지 않는다 (AUCT-005). |

**CHECK 제약**

- `ck_bid_status` — `CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'OUTBID'::character varying, 'WON'::character varying, 'LOST'::character varying])::text[])))`

**인덱스**

- `ix_bid_auction_created` — `CREATE INDEX ix_bid_auction_created ON public.bid USING btree (auction_id, created_at DESC)`
- `ix_bid_bidder` — `CREATE INDEX ix_bid_bidder ON public.bid USING btree (bidder_id, created_at DESC)`
- `ux_bid_auction_price` — `CREATE UNIQUE INDEX ux_bid_auction_price ON public.bid USING btree (auction_id, bid_price)`

---

### `brand`

브랜드 마스터. 상품 등록·검색 필터의 기준.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `name` | `varchar(100)` | NOT NULL |  | UQ | 브랜드명. 중복 불가. |
| `name_en` | `varchar(100)` |  |  |  | 브랜드 영문명. 없는 브랜드는 NULL. |

**인덱스**

- `brand_name_key` — `CREATE UNIQUE INDEX brand_name_key ON public.brand USING btree (name)`

---

### `business_info`

사업자 인증 정보 (BIZ-001).

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `business_number` | `varchar(20)` | NOT NULL |  |  | 사업자등록번호. |
| `certificate_url` | `varchar(500)` | NOT NULL |  |  | 사업자등록증 사본 URL. |
| `verification_status` | `varchar(20)` | NOT NULL | `'PENDING'` |  | PENDING \| APPROVED \| REJECTED |
| `submitted_at` | `timestamptz` | NOT NULL | `now()` |  | 인증 서류 제출 시각. |
| `verified_at` | `timestamptz` |  |  |  | 인증 승인·거절 처리 시각. |

**CHECK 제약**

- `ck_business_verification` — `CHECK (((verification_status)::text = ANY ((ARRAY['PENDING'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying])::text[])))`

---

### `category`

카테고리 마스터. parent_id 로 계층을 이룬다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `parent_id` | `bigint` |  |  | FK→category | 상위 카테고리. 최상위는 NULL. |
| `name` | `varchar(100)` | NOT NULL |  |  | 카테고리명. |
| `depth` | `smallint` | NOT NULL | `1` |  | 계층 깊이. 최상위가 1. |

---

### `chat_message`

라이브 채팅 (CHAT-001). 비회원은 시청만 가능하고 발언할 수 없다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `live_id` | `bigint` | NOT NULL |  | FK→live | 대상 라이브. |
| `member_id` | `bigint` |  |  | FK→member | 작성자. SYSTEM·AI 메시지는 NULL. |
| `sender_type` | `varchar(20)` | NOT NULL | `'USER'` |  | USER(회원 발언) \| SYSTEM(입장·퇴장·경매 안내) \| AI(자동 답변, CHAT-002) |
| `content` | `text` | NOT NULL |  |  | 메시지 본문. 차단되어도 내용은 남긴다 (is_blocked 참고). |
| `is_blocked` | `boolean` | NOT NULL | `false` |  | 금칙어·도배로 차단된 메시지 (CHAT-004). 삭제 대신 플래그로 남긴다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

**CHECK 제약**

- `ck_chat_sender_type` — `CHECK (((sender_type)::text = ANY ((ARRAY['USER'::character varying, 'SYSTEM'::character varying, 'AI'::character varying])::text[])))`
- `ck_chat_user_has_member` — `CHECK ((((sender_type)::text <> 'USER'::text) OR (member_id IS NOT NULL)))`

**인덱스**

- `ix_chat_live_created` — `CREATE INDEX ix_chat_live_created ON public.chat_message USING btree (live_id, created_at DESC)`

---

### `follow`

회원 간 팔로우 (FOLLOW-001).

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `follower_id` | `bigint` | NOT NULL |  | FK→member, UQ | 팔로우를 하는 회원 (구독자). |
| `following_id` | `bigint` | NOT NULL |  | FK→member, UQ | 팔로우 대상 회원 (판매자/크리에이터). |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

**CHECK 제약**

- `ck_follow_not_self` — `CHECK ((follower_id <> following_id))`

**인덱스**

- `ux_follow` — `CREATE UNIQUE INDEX ux_follow ON public.follow USING btree (follower_id, following_id)`

---

### `live`

라이브 방송. 경매·채팅이 열리는 "방"이다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `host_id` | `bigint` | NOT NULL |  | FK→member | 방송 진행자(판매자). |
| `title` | `varchar(200)` | NOT NULL |  |  | 방송명. 통합 검색 대상 (SEARCH-001). |
| `thumbnail_url` | `varchar(500)` |  |  |  | 방송 썸네일 URL. 홈 목록에 노출된다. |
| `status` | `varchar(20)` | NOT NULL | `'SCHEDULED'` |  | SCHEDULED(예정) \| LIVE(진행 중) \| ENDED(종료) \| CANCELED(방송 전 취소) |
| `scheduled_at` | `timestamptz` |  |  |  | 예약 방송 시작 예정 시각 (LIVE-001). 즉시 개설(LIVE-002)은 NULL. |
| `started_at` | `timestamptz` |  |  |  | 실제 방송 시작 시각. 예정 시각(scheduled_at)과 다를 수 있다. |
| `ended_at` | `timestamptz` |  |  |  | 방송 종료 시각. |
| `openvidu_room` | `varchar(100)` |  |  |  | OpenVidu v3 room name. WebRTC 세션·토큰 발급 시 사용. |
| `peak_viewer_count` | `integer` | NOT NULL | `0` |  | 최고 동시 시청자 수. 통계·발표용. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |

**CHECK 제약**

- `ck_live_status` — `CHECK (((status)::text = ANY ((ARRAY['SCHEDULED'::character varying, 'LIVE'::character varying, 'ENDED'::character varying, 'CANCELED'::character varying])::text[])))`

**인덱스**

- `ix_live_host` — `CREATE INDEX ix_live_host ON public.live USING btree (host_id, created_at DESC)`
- `ix_live_status_scheduled` — `CREATE INDEX ix_live_status_scheduled ON public.live USING btree (status, scheduled_at DESC)`
- `ix_live_title_trgm` — `CREATE INDEX ix_live_title_trgm ON public.live USING gin (title gin_trgm_ops)`

---

### `live_product`

라이브 ↔ 상품 연결 (LIVE-003). 방송 전·중 모두 추가·제외 가능하며 개수 제한이 없다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `live_id` | `bigint` | NOT NULL |  | FK→live | 대상 라이브. |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 대상 상품. |
| `sort_order` | `smallint` | NOT NULL | `0` |  | 방송 중 소개 순서. |
| `added_at` | `timestamptz` | NOT NULL | `now()` |  | 상품 연결 시각. |
| `removed_at` | `timestamptz` |  |  |  | 연결 해제 시각. 물리 삭제하지 않는 이유는 "그 시점에 연결돼 있었다"는 사실이 다시보기 타임라인(LIVE-008)의 근거이기 때문. |

**인덱스**

- `ux_live_product_active` — `CREATE UNIQUE INDEX ux_live_product_active ON public.live_product USING btree (live_id, product_id) WHERE (removed_at IS NULL)`

---

### `member`

서비스 회원. 판매자·구매자 구분 없이 한 테이블을 쓴다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `email` | `varchar(255)` | NOT NULL |  | UQ | 로그인 ID 겸 연락 수단. 경매 화면에는 노출하지 않는다. |
| `password` | `varchar(255)` |  |  |  | 자체 로그인용 해시. SSO 전용 계정은 NULL. |
| `nickname` | `varchar(30)` |  |  | UQ | 공개 표시명. 최고 입찰자·낙찰자 표시에 쓰는 유일한 신원 정보 (AUCT-011). |
| `name` | `varchar(50)` |  |  |  | 실명. 배송·정산용이며 외부 노출 금지. |
| `phone_number` | `varchar(20)` |  |  |  | 연락처. 배송·정산 확인용이며 외부 노출 금지. |
| `address` | `varchar(200)` |  |  |  | 기본 주소(도로명/지번). 온보딩(ONBOARD-001)에서 입력. |
| `detail_address` | `varchar(100)` |  |  |  | 상세 주소(동/호수 등). |
| `postal_code` | `varchar(10)` |  |  |  | 우편번호. 주소 검색을 안 쓰고 직접 입력하면 NULL 허용. |
| `gender` | `varchar(10)` |  |  |  | MALE \| FEMALE |
| `member_type` | `varchar(20)` | NOT NULL | `'GENERAL'` |  | GENERAL(일반) \| BUSINESS(사업자) |
| `status` | `varchar(20)` | NOT NULL | `'ACTIVE'` |  | ACTIVE \| SUSPENDED(정지) \| WITHDRAWN(탈퇴) |
| `profile_image_url` | `varchar(500)` |  |  |  | 프로필 이미지 URL. |
| `onboarding_done` | `boolean` | NOT NULL | `false` |  | 온보딩(관심 브랜드·카테고리·신체 정보) 완료 여부. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |
| `deleted_at` | `timestamptz` |  |  |  | 탈퇴 시각. 입찰·주문 이력이 FK 로 남아 물리 삭제하지 않는다. |

**CHECK 제약**

- `ck_member_gender` — `CHECK (((gender)::text = ANY ((ARRAY['MALE'::character varying, 'FEMALE'::character varying])::text[])))`
- `ck_member_status` — `CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'SUSPENDED'::character varying, 'WITHDRAWN'::character varying])::text[])))`
- `ck_member_type` — `CHECK (((member_type)::text = ANY ((ARRAY['GENERAL'::character varying, 'BUSINESS'::character varying])::text[])))`

**인덱스**

- `ix_member_nickname_trgm` — `CREATE INDEX ix_member_nickname_trgm ON public.member USING gin (nickname gin_trgm_ops)`
- `member_email_key` — `CREATE UNIQUE INDEX member_email_key ON public.member USING btree (email)`
- `member_nickname_key` — `CREATE UNIQUE INDEX member_nickname_key ON public.member USING btree (nickname)`

---

### `member_body_profile`

전신 사진·신체 정보 (ONBOARD-003, TRYON-001~002). 가상 시착 입력값.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `body_photo_url` | `varchar(500)` |  |  |  | 전신 사진 URL. 미등록이면 시착 불가. |
| `height_cm` | `smallint` |  |  |  | 키(cm). |
| `weight_kg` | `smallint` |  |  |  | 몸무게(kg). |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |

---

### `member_interest_brand`

온보딩 관심 브랜드 (ONBOARD-002). 추천(REC-001) 입력.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `brand_id` | `bigint` | NOT NULL |  | FK→brand, PK | 브랜드. |

---

### `member_interest_category`

온보딩 관심 카테고리 (ONBOARD-002). 추천(REC-001) 입력.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `category_id` | `bigint` | NOT NULL |  | FK→category, PK | 카테고리. |

---

### `member_social_account`

외부 계정 연결 (AUTH-003, AUTH-004). 한 회원이 여러 provider 를 가질 수 있다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `member_id` | `bigint` | NOT NULL |  | FK→member | 대상 회원. |
| `provider` | `varchar(30)` | NOT NULL |  | UQ | SSO 공급자. 현재 SSAFY 만 허용. |
| `provider_user_id` | `varchar(255)` | NOT NULL |  | UQ | 공급자 측 고유 ID. provider 와 묶어 유일하다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

**CHECK 제약**

- `ck_social_provider` — `CHECK (((provider)::text = 'SSAFY'::text))`

**인덱스**

- `uq_social_provider_user` — `CREATE UNIQUE INDEX uq_social_provider_user ON public.member_social_account USING btree (provider, provider_user_id)`

---

### `notification`

회원 알림 (NOTI-*). 라이브·경매 트리거는 정윤 도메인에서 이벤트로 발행하고 생성은 서윤 담당.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `member_id` | `bigint` | NOT NULL |  | FK→member | 대상 회원. |
| `type` | `varchar(40)` | NOT NULL |  |  | 알림 종류 (NOTI-002 방송, NOTI-003 경매 등). |
| `title` | `varchar(200)` | NOT NULL |  |  | 알림 제목. |
| `body` | `varchar(500)` |  |  |  | 알림 본문. |
| `ref_type` | `varchar(30)` |  |  |  | 연결 대상 종류 (LIVE / AUCTION / ORDER ...). 클릭 시 이동 대상. |
| `ref_id` | `bigint` |  |  |  | 연결 대상 ID. |
| `is_read` | `boolean` | NOT NULL | `false` |  | 읽음 여부. 알림함 기본 조회가 "안 읽은 것 먼저"라 인덱스 선두에 있다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

**인덱스**

- `ix_notification_member` — `CREATE INDEX ix_notification_member ON public.notification USING btree (member_id, is_read, created_at DESC)`

---

### `order_shipment`

배송지·송장 정보 (SHIP-*). 주문 1건당 1행.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `order_id` | `bigint` | NOT NULL |  | FK→orders, PK | 대상 주문. |
| `recipient_name` | `varchar(50)` | NOT NULL |  |  | 수령인 이름. |
| `recipient_phone` | `varchar(20)` | NOT NULL |  |  | 수령인 연락처. |
| `zipcode` | `varchar(10)` | NOT NULL |  |  | 우편번호. |
| `address1` | `varchar(255)` | NOT NULL |  |  | 기본 주소. |
| `address2` | `varchar(255)` |  |  |  | 상세 주소. |
| `courier` | `varchar(50)` |  |  |  | 택배사. 송장 등록 전에는 NULL. |
| `tracking_number` | `varchar(50)` |  |  |  | 운송장 번호. 판매자가 등록한다. |
| `shipped_at` | `timestamptz` |  |  |  | 발송 시각. 송장 등록 시점. |
| `delivered_at` | `timestamptz` |  |  |  | 배송 완료 시각. orders.auto_confirm_at 계산 기준. |

---

### `orders`

주문. 낙찰(AUCT-012) 또는 상시 구매로 생성된다. order 가 SQL 예약어라 테이블명이 orders 다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `buyer_id` | `bigint` | NOT NULL |  | FK→member | 구매자. 낙찰 주문이면 auction.winner_id 와 같다. |
| `seller_id` | `bigint` | NOT NULL |  | FK→member | 판매자. 상품 등록자와 같다. |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 대상 상품. |
| `auction_id` | `bigint` |  |  | FK→auction | 낙찰로 생성된 주문의 경매. 상시 판매 주문은 NULL. |
| `order_price` | `bigint` | NOT NULL |  |  | 결제 금액(원). |
| `status` | `varchar(30)` | NOT NULL | `'PAID'` |  | PAID → SHIPPING → DELIVERED → CONFIRMED → SETTLED (+ REFUNDED / CANCELED) |
| `auto_confirm_at` | `timestamptz` |  |  |  | 자동 구매 확정 예정 시각(배송 완료 + 7일). 배송 완료 시점에 채워 넣고 스케줄러가 이 컬럼으로 대상을 찾는다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |

**CHECK 제약**

- `ck_order_not_self` — `CHECK ((buyer_id <> seller_id))`
- `ck_order_status` — `CHECK (((status)::text = ANY ((ARRAY['PAID'::character varying, 'SHIPPING'::character varying, 'DELIVERED'::character varying, 'CONFIRMED'::character varying, 'SETTLED'::character varying, 'REFUNDED'::character varying, 'CANCELED'::character varying])::text[])))`

**인덱스**

- `ix_orders_auto_confirm` — `CREATE INDEX ix_orders_auto_confirm ON public.orders USING btree (auto_confirm_at) WHERE ((status)::text = 'DELIVERED'::text)`
- `ix_orders_buyer` — `CREATE INDEX ix_orders_buyer ON public.orders USING btree (buyer_id, created_at DESC)`
- `ix_orders_seller` — `CREATE INDEX ix_orders_seller ON public.orders USING btree (seller_id, created_at DESC)`

---

### `point_account`

회원별 포인트 잔액. 기능정의서 §4.9 포인트 상태 6종을 "상태 컬럼"이 아니라 "잔액 버킷"으로 구현했다. 금액이 버킷 사이를 이동한다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `available` | `bigint` | NOT NULL | `0` |  | [사용 가능] 충전·보류 해제·환불로 들어온다. 입찰 가능액의 기준. |
| `bid_held` | `bigint` | NOT NULL | `0` |  | [입찰 보류] 최고 입찰자가 되면 available 에서 옮겨진다 (AUCT-007). |
| `trade_escrow` | `bigint` | NOT NULL | `0` |  | [거래 보관] 낙찰·구매 후 구매 확정 전까지 묶여 있는 대금. |
| `settling` | `bigint` | NOT NULL | `0` |  | [판매자 정산] 구매 확정 후 판매자에게 넘어갈 몫. |
| `withdrawing` | `bigint` | NOT NULL | `0` |  | [출금 처리] 출금 요청 후 처리 중인 금액. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |

**CHECK 제약**

- `ck_point_non_negative` — `CHECK (((available >= 0) AND (bid_held >= 0) AND (trade_escrow >= 0) AND (settling >= 0) AND (withdrawing >= 0)))`

---

### `point_hold`

입찰 보류 건. 입찰 내역 ↔ 포인트 잔액을 잇는 테이블이며 경매 동시성 제어의 핵심.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `member_id` | `bigint` | NOT NULL |  | FK→member | 대상 회원. |
| `auction_id` | `bigint` | NOT NULL |  | FK→auction | 대상 경매. |
| `bid_id` | `bigint` | NOT NULL |  | FK→bid | 근거 입찰. |
| `amount` | `bigint` | NOT NULL |  |  | 보류 금액(원). 해당 입찰가와 같다. |
| `status` | `varchar(20)` | NOT NULL | `'HELD'` |  | HELD(보류 중 = 최고 입찰자) \| RELEASED(상위 입찰로 해제, AUCT-008) \| CONVERTED(낙찰되어 거래 대금 전환, AUCT-012) |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `released_at` | `timestamptz` |  |  |  | 보류 해제 시각. |

**CHECK 제약**

- `ck_point_hold_status` — `CHECK (((status)::text = ANY ((ARRAY['HELD'::character varying, 'RELEASED'::character varying, 'CONVERTED'::character varying])::text[])))`

**인덱스**

- `ix_point_hold_auction` — `CREATE INDEX ix_point_hold_auction ON public.point_hold USING btree (auction_id, status)`
- `ux_point_hold_member_active` — `CREATE UNIQUE INDEX ux_point_hold_member_active ON public.point_hold USING btree (member_id) WHERE ((status)::text = 'HELD'::text)`

---

### `point_transaction`

포인트 원장. 모든 증감을 append-only 로 남긴다. 잔액 이상 발생 시 대조 근거.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `member_id` | `bigint` | NOT NULL |  | FK→member | 대상 회원. |
| `type` | `varchar(30)` | NOT NULL |  |  | CHARGE \| BID_HOLD \| BID_RELEASE \| PAYMENT \| SETTLEMENT \| REFUND \| WITHDRAW |
| `amount` | `bigint` | NOT NULL |  |  | 증감액(원). 부호 있음. |
| `balance_after` | `bigint` | NOT NULL |  |  | 기록 시점의 available 잔액. 원장 재계산 없이 시점 잔액을 알 수 있다. |
| `ref_type` | `varchar(30)` |  |  |  | 연결 대상 종류 (AUCTION / ORDER / BID ...). |
| `ref_id` | `bigint` |  |  |  | 연결 대상 ID. FK 를 걸지 않아 무결성은 애플리케이션 책임. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

**CHECK 제약**

- `ck_point_tx_type` — `CHECK (((type)::text = ANY ((ARRAY['CHARGE'::character varying, 'BID_HOLD'::character varying, 'BID_RELEASE'::character varying, 'PAYMENT'::character varying, 'SETTLEMENT'::character varying, 'REFUND'::character varying, 'WITHDRAW'::character varying])::text[])))`

**인덱스**

- `ix_point_tx_member` — `CREATE INDEX ix_point_tx_member ON public.point_transaction USING btree (member_id, created_at DESC)`

---

### `product`

판매 상품. 라이브·경매·주문이 모두 이 테이블을 FK 로 문다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `seller_id` | `bigint` | NOT NULL |  | FK→member | 판매자. |
| `category_id` | `bigint` | NOT NULL |  | FK→category | 카테고리. |
| `brand_id` | `bigint` |  |  | FK→brand | 브랜드. |
| `title` | `varchar(200)` | NOT NULL |  |  | 상품명. 통합 검색 대상이며 pg_trgm GIN 인덱스가 걸려 있다 (SEARCH-001). |
| `description` | `text` |  |  |  | 상품 상세 설명. |
| `condition_grade` | `varchar(20)` |  |  |  | 중고 상태 등급. ⚠️ 등급 체계 미확정이라 자유 문자열. |
| `size_label` | `varchar(50)` |  |  |  | 사이즈 표기(S/M/L, 95/100 등). 브랜드마다 달라 문자열로 둔다. |
| `color` | `varchar(50)` |  |  |  | 색상(자유 문자열). |
| `material` | `varchar(50)` |  |  |  | 소재(자유 문자열). |
| `measurements` | `jsonb` |  |  |  | 실측 치수(cm). 항목(총장/어깨너비 등)이 상품마다 달라 JSONB로 저장. |
| `sale_type` | `varchar(20)` |  |  |  | DIRECT_SALE(상시 판매) \| AUCTION(경매) |
| `sale_status` | `varchar(30)` | NOT NULL | `'DRAFT'` |  | DRAFT \| ON_SALE \| AUCTION_SCHEDULED \| AUCTION_IN_PROGRESS \| SOLD |
| `price` | `bigint` |  |  |  | 상시 판매가(원). 경매 예정 상품은 NULL — 가격대 필터에서 별도 처리한다 (SEARCH-002). |
| `view_count` | `integer` | NOT NULL | `0` |  | 누적 조회수(집계값). ⚠️ 회원별 조회 이력은 남지 않는다 — REC-001 착수 시 재검토 필요. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `updated_at` | `timestamptz` | NOT NULL | `now()` |  | 최종 수정 시각. |
| `deleted_at` | `timestamptz` |  |  |  | 삭제 시각. 주문 이력 보존을 위해 물리 삭제하지 않는다. |

**CHECK 제약**

- `ck_product_price_by_type` — `CHECK ((((sale_type)::text <> 'DIRECT_SALE'::text) OR (price IS NOT NULL)))`
- `ck_product_sale_status` — `CHECK (((sale_status)::text = ANY ((ARRAY['DRAFT'::character varying, 'ON_SALE'::character varying, 'AUCTION_SCHEDULED'::character varying, 'AUCTION_IN_PROGRESS'::character varying, 'SOLD'::character varying])::text[])))`
- `ck_product_sale_type` — `CHECK (((sale_type)::text = ANY ((ARRAY['DIRECT_SALE'::character varying, 'AUCTION'::character varying])::text[])))`

**인덱스**

- `ix_product_brand` — `CREATE INDEX ix_product_brand ON public.product USING btree (brand_id, sale_status)`
- `ix_product_category` — `CREATE INDEX ix_product_category ON public.product USING btree (category_id, sale_status)`
- `ix_product_price` — `CREATE INDEX ix_product_price ON public.product USING btree (price) WHERE (price IS NOT NULL)`
- `ix_product_seller` — `CREATE INDEX ix_product_seller ON public.product USING btree (seller_id, created_at DESC)`
- `ix_product_status_created` — `CREATE INDEX ix_product_status_created ON public.product USING btree (sale_status, created_at DESC) WHERE (deleted_at IS NULL)`
- `ix_product_title_trgm` — `CREATE INDEX ix_product_title_trgm ON public.product USING gin (title gin_trgm_ops)`

---

### `product_defect`

판매자가 직접 입력한 하자 목록 (PROD-001).

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 대상 상품. |
| `content` | `text` | NOT NULL |  |  | 하자 내용(자유 문자열). |
| `sort_order` | `smallint` | NOT NULL | `0` |  | 노출 순서. |

---

### `product_image`

상품 이미지. 시착(TRYON-003) 입력으로도 쓰인다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 대상 상품. |
| `image_key` | `varchar(500)` | NOT NULL |  |  | S3 오브젝트 key(전체 URL 아님). public 버킷에 저장하며 응답 시점에 고정 URL로 조립한다. |
| `sort_order` | `smallint` | NOT NULL | `0` |  | 노출 순서. |
| `is_primary` | `boolean` | NOT NULL | `false` |  | 대표 이미지 여부. 목록·썸네일에 쓴다. |

---

### `tryon_result`

AI 가상 시착 합성 결과물. 생성(POST) 자체는 AI 계약 확정 전이라 저장/조회/삭제만 다룬다.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | NOT NULL |  | PK | PK. IDENTITY 자동 채번. |
| `member_id` | `bigint` | NOT NULL |  | FK→member | 결과물 소유자. 본인만 조회 가능 (presigned GET URL). |
| `product_id` | `bigint` | NOT NULL |  | FK→product | 합성에 사용된 상품. |
| `image_key` | `varchar(500)` | NOT NULL |  |  | S3 오브젝트 key(전체 URL 아님). private 버킷에 저장하며 조회 시 presigned GET URL을 매번 새로 발급한다. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |
| `deleted_at` | `timestamptz` |  |  |  | 사용자가 수동 삭제한 시각. 자동 만료 정책은 없다. |

**인덱스**

- `ix_tryon_result_member` — `CREATE INDEX ix_tryon_result_member ON public.tryon_result USING btree (member_id, created_at DESC) WHERE (deleted_at IS NULL)`

---

### `wish`

찜 (MY-009). 추천(REC-001) 입력.

| 컬럼 | 타입 | NULL | 기본값 | 키 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `member_id` | `bigint` | NOT NULL |  | FK→member, PK | 대상 회원. |
| `product_id` | `bigint` | NOT NULL |  | FK→product, PK | 대상 상품. |
| `created_at` | `timestamptz` | NOT NULL | `now()` |  | 생성 시각. |

