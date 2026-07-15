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
- AI 서버(FastAPI)와의 연동 (가상 시착 요청, 상품 설명 초안 등)

## 기술 스택

- Java 21, Spring Boot 4.1.0 (Gradle, Groovy DSL)
- Spring Web, Spring Data JPA (+ QueryDSL 검토), Spring Security, Validation, Lombok
- 실시간: Spring WebSocket(STOMP) — 채팅/경매 이벤트
- Redis(Spring Data Redis): 입찰 동시성 제어(분산 락 도입 검토), 서버 간 이벤트 Pub/Sub, 캐시
- PostgreSQL Driver
- 파일 저장: S3 or MinIO (미확정)

> Spring Initializr(start.spring.io)가 현재 3.x 라인을 더 이상 제공하지 않아 최신 4.1.0으로 생성함.

## 실행 방법

1. 루트의 `docker-compose.yml`로 Postgres/Redis 실행: `docker compose up -d postgres redis`
2. `.env.example`을 `.env`로 복사 후 값 조정
3. `./gradlew bootRun`

## 디렉터리 구조

```
BE/
├── build.gradle
├── settings.gradle
├── src/main/java/com/ssafy/backend/BackendApplication.java
├── src/main/resources/application.yml
└── src/test/java/com/ssafy/backend/
```

도메인별 패키지(controller/service/domain 등)는 아직 나누지 않음. 구조 확정 시 이 섹션 갱신.
