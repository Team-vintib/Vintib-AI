# HS020 · FE 배포 (Caddy 뒤 nginx 정적 서빙)

- **에픽**: `S15P11A108-27` 개발 기반 및 인프라 구축 (공동 인프라)
- **브랜치**: `feat/27-fe-deploy` (develop-FE 기준)
- **성격**: 인프라 설정 신설. FE를 EC2에 처음으로 배포한다.

## 배경 / 목표

- 현재 배포 서버(`i15a108.p.ssafy.io`)는 **Caddy 뒤에 BE·AI·MinIO만** 올라가 있고
  **FE는 배포돼 있지 않다** (Caddyfile이 `/api`·`/ai`·`/vintib-*` 외 나머지를 전부 backend로 보냄).
- 목표: FE 빌드 산출물(`dist`)을 **같은 도메인에서 Caddy가 서빙**하게 하여, 브라우저로
  `https://i15a108.p.ssafy.io` 접속 시 FE가 뜨고 `/api`는 BE로 가게 한다.
- 방식(합의됨): **방법 A — FE 전용 nginx 컨테이너 + Caddy 프록시.** 지금 스택이 전부
  docker compose 서비스라 일관적이고, 배포 스크립트(`compose build && up`)에 자연스럽게 얹힌다.

## 라우팅 목표

```
https://i15a108.p.ssafy.io
  ├─ /api/*        → backend:8080   (유지)
  ├─ /ai/*         → ai:8000        (유지)
  ├─ /vintib-*/*   → minio:9000     (유지)
  └─ 나머지 /*     → frontend:80    (신규: FE 정적 서빙, SPA fallback)
```

## 작업 내용 (구두 설명)

1. **`FE/Dockerfile` (멀티스테이지) 신설**
   - 1단계(builder): `node` 이미지에서 `npm ci && npm run build` → `dist` 생성.
     빌드 시 프로덕션 env를 `VITE_API_BASE_URL=/api`(상대경로)로 지정 — 같은 도메인이라
     절대 URL 불필요. (빌드 인자 또는 `.env.production`으로 주입)
   - 2단계(runtime): `nginx:alpine`에 `dist`만 복사. node는 최종 이미지에 미포함.
2. **`FE/nginx.conf` 신설** — 정적 서빙 + **SPA fallback**(`try_files $uri /index.html`),
   gzip, 정적 asset 캐시 헤더. (Vue Router history 모드라 fallback 필수)
3. **`docker-compose.prod.yml`에 `frontend` 서비스 추가** — `build: ./FE`, `vintib-net`
   연결, healthcheck, 호스트 포트 미publish(Caddy만 외부 노출). base compose에도 필요 시 반영.
4. **`infra/caddy/Caddyfile` 수정** — 기존 `handle { reverse_proxy backend:8080 }`을
   `/api` 전용으로 좁히고(또는 `handle /api/*`), **나머지 `/`는 `reverse_proxy frontend:80`**.
   `/ws`(STOMP)는 backend로 유지되도록 명시.
5. **CI 배포 트리거 확인/보완** — 현재 deploy 잡은 `develop-BE` 병합에서만 돈다.
   FE 변경도 반영되려면 (a) `develop-FE` 병합에도 deploy 트리거 추가, 또는 (b) 통합 배포
   브랜치 전략 확정. `deploy.sh`의 `compose build`는 frontend 이미지까지 빌드하므로
   스크립트 자체 수정은 최소.
6. **로컬 검증** — `docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend`
   후 컨테이너 기동, Caddy 라우팅으로 FE·`/api`·`/ws` 동작 확인. 새로고침(SPA) 확인.
7. **📄 최종 문서화 (필수 산출물)** — 배포 성공 후, **초보자·미경험 팀원도 따라 할 수 있게**
   전 과정을 자세하고 쉽게 정리한 가이드 문서를 남긴다 (개념→파일별 역할→명령어→트러블슈팅).
   위치: `FE/docs/deploy.md` (또는 팀 합의 위치).

## 구현 목록

- [ ] `FE/Dockerfile` 멀티스테이지(node build → nginx) 작성
- [ ] `FE/nginx.conf` (SPA fallback + gzip + 캐시) 작성
- [ ] 프로덕션 빌드 env `VITE_API_BASE_URL=/api` 주입 방식 확정(빌드 인자/.env.production)
- [ ] `docker-compose.prod.yml`에 `frontend` 서비스 추가 (+ base compose 정합)
- [ ] `Caddyfile` 라우팅 수정 (`/api`·`/ai`·`/vintib-*`·`/ws` 유지, 나머지 → frontend)
- [ ] CI deploy 트리거에 `develop-FE` 반영(또는 배포 전략 확정)
- [ ] 로컬에서 prod compose로 전체 라우팅·SPA 새로고침 검증
- [ ] EC2 실제 배포 후 동작 확인
- [ ] 📄 초보자용 배포 가이드 문서 작성 (약속된 최종 산출물)

## 확인이 필요한 미결정 사항

1. **빌드 env 주입 방식**: Dockerfile `ARG`+`.env.production` 중 무엇으로 `VITE_API_BASE_URL=/api`를
   줄지. → 기본안: `FE/.env.production`에 `/api` 두고 빌드가 자동으로 읽게.
2. **배포 트리거**: `develop-FE` 병합 시 배포를 붙일지, BE와 통합 배포로 갈지. → BE(정윤)와 합의 필요.
3. **base `docker-compose.yml`에도 frontend를 넣을지**(로컬 override 포트 노출 포함) vs prod 전용.
   → 기본안: prod 전용으로 시작, 로컬은 `npm run dev` 유지.
4. **인프라 파일(Caddyfile/compose/CI) 직접 수정** = 에픽27 공동으로 진행하되, 병합 전 **BE와
   Caddy 라우팅 변경 사전 공유** 필요(잘못하면 API/이미지 라우팅이 깨질 수 있음).
