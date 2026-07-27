# BE

빈티지·세컨핸드 의류 라이브 경매 플랫폼 백엔드.

## 담당 범위

기능정의서 4장 기준 아래 도메인의 API를 담당한다.

- 회원/인증, 마이페이지 (AUTH, USER, MY)
- 홈·검색·팔로우·알림·추천 (HOME, SEARCH, FOLLOW, NOTI, REC)
- 상품 등록 및 판매, 라이브 기반 상품 생성 (PROD, LPROD)
- 라이브 방송/채팅 시그널링 및 상태 관리 (LIVE, CHAT)
- 실시간 경매 (AUCT) — 입찰, 포인트 홀드, 자동 연장, 낙찰 처리
- 포인트·구매·배송·정산 (POINT, BUY, PAY, SHIP, ORDER, SETTLE, REFUND)
- AI 서버(FastAPI)와의 연동 (가상 시착, 추천, 라이브 댓글 관리)
- AI 서버(FastAPI)와의 연동 (가상 시착, 추천, 라이브 댓글 관리)

## 기술 스택

- Java 21, Spring Boot 4.1.0 (Gradle, Groovy DSL)
- Spring Web, Spring Data JPA (+ QueryDSL 검토), Spring Security, Validation, Lombok
- 실시간: Spring WebSocket(STOMP) — 채팅/경매 이벤트
- Redis(Spring Data Redis): 입찰 동시성 제어(분산 락 도입 검토), 서버 간 이벤트 Pub/Sub, 캐시, 이메일 인증코드/토큰 저장
- PostgreSQL 18 Driver
- Spring Mail: 이메일 인증코드 발송
- springdoc-openapi(Swagger UI): API 문서화 (`/swagger-ui/index.html`, `/v3/api-docs`)
- 파일 저장: **S3 미제공** — EC2 로컬 볼륨 기준으로 설계 (방식 미확정)

> Spring Initializr(start.spring.io)가 현재 3.x 라인을 더 이상 제공하지 않아 최신 4.1.0으로 생성함.

## 실행 방법

### 1) 전부 컨테이너로 (권장 — EC2와 동일 구성)

레포 루트에서:

```bash
cp .env.example .env && docker compose up -d
```

`docker-compose.override.yml`이 자동 병합되어 로컬 개발용 포트가 열린다.

| 서비스 | 로컬 주소 |
| --- | --- |
| Spring Boot | http://localhost:8080 |
| FastAPI | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

배선 확인:

```bash
curl -s http://localhost:8080/actuator/health && curl -s http://localhost:8080/api/health
```

`/actuator/health`는 PostgreSQL·Redis를, `/api/health`는 FastAPI 도달 여부를 보여준다.

### 2) 인프라만 컨테이너 + Spring은 IDE에서

```bash
docker compose up -d postgres redis ai
```

이후 `BE/`에서 `./gradlew bootRun` (기본 프로파일 `local`).

### 3) EC2 운영 기동

override를 타지 않도록 `-f`를 반드시 명시한다.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> [!WARNING]
> 베이스 `docker-compose.yml`에는 호스트 포트를 절대 추가하지 않는다. Docker는 포트 publish 시 iptables를 직접 조작해 UFW를 우회하므로, PostgreSQL·Redis·FastAPI가 그대로 외부에 노출된다. 로컬용 포트는 `docker-compose.override.yml`에만 둔다.

## 프로파일

| 프로파일 | ddl-auto | actuator 노출 | 용도 |
| --- | --- | --- | --- |
| `local` | `update` | health, info, metrics, env, beans | 개발 |
| `prod` | `validate` | health (상세 숨김) | EC2 |

## DB 설계

테이블 23개 기준. 상세는 [`docs/db/`](./docs/db)에 있다.

| 문서 | 내용 |
| --- | --- |
| [ERD·상태 설계](./docs/db/erd.md) | ERD, 상태 전이, 정책을 DB 제약으로 옮긴 근거, 미확인 가정 |
| [데이터 사전](./docs/db/data-dictionary.md) | 테이블별 컬럼·타입·제약·기본값·설명 (자동 생성) |
| [`schema.sql`](./docs/db/schema.sql) | 스키마 원본 — 단일 기준 |

> [!IMPORTANT]
> `data-dictionary.md`와 `docs/db/img/`는 **자동 생성물이다.** 직접 고치지 말고 `bash docs/db/regen.sh` / `bash docs/db/export-erd.sh`로 다시 뽑는다.

경매 동시성 정책(`LIVE-004`, `AUCT-004/006/008/009`)은 애플리케이션 검증뿐 아니라 **DB 제약으로도 막혀 있다.** 입찰 로직을 손볼 때는 [`erd.md` §4](./docs/db/erd.md)를 먼저 읽을 것 — 특히 포인트 보류 해제 순서를 잘못 잡으면 제약이 무력화된다.
### 1) 전부 컨테이너로 (권장 — EC2와 동일 구성)

레포 루트에서:

```bash
cp .env.example .env && docker compose up -d
```

`docker-compose.override.yml`이 자동 병합되어 로컬 개발용 포트가 열린다.

| 서비스 | 로컬 주소 |
| --- | --- |
| Spring Boot | http://localhost:8080 |
| FastAPI | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

배선 확인:

```bash
curl -s http://localhost:8080/actuator/health && curl -s http://localhost:8080/api/health
```

`/actuator/health`는 PostgreSQL·Redis를, `/api/health`는 FastAPI 도달 여부를 보여준다.

### 2) 인프라만 컨테이너 + Spring은 IDE에서

```bash
docker compose up -d postgres redis ai
```

이후 `BE/`에서 `./gradlew bootRun` (기본 프로파일 `local`).

### 3) EC2 운영 기동

override를 타지 않도록 `-f`를 반드시 명시한다.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> [!WARNING]
> 베이스 `docker-compose.yml`에는 호스트 포트를 절대 추가하지 않는다. Docker는 포트 publish 시 iptables를 직접 조작해 UFW를 우회하므로, PostgreSQL·Redis·FastAPI가 그대로 외부에 노출된다. 로컬용 포트는 `docker-compose.override.yml`에만 둔다.

## 프로파일

| 프로파일 | ddl-auto | actuator 노출 | 용도 |
| --- | --- | --- | --- |
| `local` | `update` | health, info, metrics, env, beans | 개발 |
| `prod` | `validate` | health (상세 숨김) | EC2 |

## DB 설계

테이블 23개 기준. 상세는 [`docs/db/`](./docs/db)에 있다.

| 문서 | 내용 |
| --- | --- |
| [ERD·상태 설계](./docs/db/erd.md) | ERD, 상태 전이, 정책을 DB 제약으로 옮긴 근거, 미확인 가정 |
| [데이터 사전](./docs/db/data-dictionary.md) | 테이블별 컬럼·타입·제약·기본값·설명 (자동 생성) |
| [`schema.sql`](./docs/db/schema.sql) | 스키마 원본 — 단일 기준 |

> [!IMPORTANT]
> `data-dictionary.md`와 `docs/db/img/`는 **자동 생성물이다.** 직접 고치지 말고 `bash docs/db/regen.sh` / `bash docs/db/export-erd.sh`로 다시 뽑는다.

경매 동시성 정책(`LIVE-004`, `AUCT-004/006/008/009`)은 애플리케이션 검증뿐 아니라 **DB 제약으로도 막혀 있다.** 입찰 로직을 손볼 때는 [`erd.md` §4](./docs/db/erd.md)를 먼저 읽을 것 — 특히 포인트 보류 해제 순서를 잘못 잡으면 제약이 무력화된다.

## 디렉터리 구조

```
BE/
├── build.gradle
├── settings.gradle
├── src/main/java/com/ssafy/backend/
│   ├── BackendApplication.java
│   ├── auth/                    # 회원가입/로그인/이메일 인증/JWT (AUTH) — 서윤
│   │   ├── controller/
│   │   ├── service/
│   │   ├── jwt/                 # JwtTokenProvider, JwtAuthenticationFilter/EntryPoint
│   │   └── dto/
│   ├── member/                  # 회원 엔티티/레포지토리 (USER) — 서윤
│   │   ├── entity/
│   │   └── repository/
│   ├── product/                 # 상품 등록/조회 (PROD) — 서윤
│   │   ├── controller/
│   │   ├── service/
│   │   ├── entity/
│   │   ├── repository/
│   │   └── dto/
│   ├── home/                    # 홈/팔로잉 콘텐츠 조회 (HOME) — 정윤
│   │   ├── controller/
│   │   ├── service/
│   │   └── dto/response/        # 카드 DTO는 현재 Mock 응답용 (2주차 실데이터 연결)
│   ├── live/                    # 라이브 방 개설/조회/상태 전이 (LIVE) — 정윤
│   │   ├── entity/              # Live, LiveStatus
│   │   └── repository/
│   ├── auction/                 # 경매 조건 설정/진행 (AUCT) — 정윤
│   │   ├── entity/              # Auction, AuctionStatus
│   │   └── repository/
│   └── global/                  # 도메인 무관 공통 — BE 2인 공유
│       ├── client/              # AiClient — Spring → FastAPI
│       ├── config/              # SecurityConfig, JpaAuditingConfig, AiClientConfig
│       ├── entity/              # BaseTimeEntity 등 공통 베이스 엔티티
│       ├── exception/           # ErrorCode, CustomException, GlobalExceptionHandler
│       ├── health/              # HealthController
│       └── response/            # ApiResponse, ErrorResponse
├── src/main/resources/application.yml
└── src/test/java/com/ssafy/backend/
```

도메인 패키지는 {domain}/ 아래에 controller / service / repository / entity / dto로 나눈다. 상세 규칙은 `.claude/skills/scaffold` 참고.

담당 분배:

```
{auth,member,product,point,order}/   ← 서윤
{live,auction,chat,home,search}/     ← 정윤
```

> `global/` 아래는 두 사람이 공유한다. 특히 `ErrorCode`는 단일 enum을 함께 쓰므로 도메인별 접두어 구역(C/U/L/A/W/O/T)을 지키고, 자기 구역에만 추가한다.

## 인증 방식

로그인(`POST /api/auth/signin`) 시 Access/Refresh 토큰을 발급한다. 이후 요청은 `Authorization: Bearer <accessToken>` 헤더로 인증한다.

- Access Token: 15분, Refresh Token: 14일(둘 다 서명 검증 + Refresh는 Redis 저장값과 대조)
- 토큰 재발급: `POST /api/auth/reissue` (바디에 refreshToken)
- 로그아웃: `POST /api/auth/logout` — Redis에 저장된 Refresh Token만 삭제(Access Token은 자연 만료까지 유효)
- `/api/auth/signup`, `/api/auth/signin`, `/api/auth/reissue`, `/api/auth/email/**`, `/api/health`, `/api/home`, `/actuator/**`, swagger 경로는 인증 없이 접근 가능. 그 외 모든 API는 인증 필요. (`/api/home/following`은 정확 일치가 아니라 인증 필요)

## 공통 응답 규격

성공·실패 모두 `ApiResponse<T>` 한 겹으로 감싼다.

```json
{ "success": true,  "data": { }, "error": null }
{ "success": false, "data": null, "error": { "code": "A002", "message": "입찰 금액이 현재 최고가보다 낮습니다.", "errors": null } }
```