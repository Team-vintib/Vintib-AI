# FE 배포 가이드 (초보용)

프론트엔드를 배포 서버(`i15a108.p.ssafy.io`)에 올리는 과정 정리. FE 팀 공유용.

## 한 줄 요약

FE를 빌드해 **nginx 컨테이너**로 만들고, **Caddy**가 그 컨테이너로 라우팅해서 **BE와 같은 도메인**에서 서빙한다.

```
브라우저 → Caddy → /api·/ws·... → backend
                 → 그 외 /       → frontend(nginx, 우리 화면)
```

## 전체 흐름 (순서)

1. **FE 배포 파일 만들기** (`FE/` 안): `Dockerfile`, `nginx.conf`, `.dockerignore`, `.env.production`
2. **docker에 등록**: `docker-compose.prod.yml`에 `frontend` 서비스 추가 + `Caddyfile` catch-all을 `frontend:80`으로
3. **`develop-FE`로 MR → 병합**
4. **`develop-FE` → `main` 병합 = 배포** (main 병합 시 CI가 자동 배포. `[DEPLOY]` 커밋)
5. 서버에서 frontend 컨테이너가 뜨고 Caddy가 라우팅 → **사이트에 FE 뜸**

> 로컬 개발은 그대로 `npm run dev` (docker 몰라도 됨). docker/배포는 서버에서 한 번만 설정.

## 각 파일 역할 (한 줄씩)

| 파일 | 역할 |
| --- | --- |
| `FE/Dockerfile` | node로 빌드(`dist`) → nginx로 서빙. **멀티스테이지**(최종 이미지에 node 없음) |
| `FE/nginx.conf` | **SPA fallback**(`/lives/1` 새로고침 404 방지), `/healthz`, 캐시 정책, gzip은 끔(Caddy가 함) |
| `FE/.env.production` | 배포 빌드는 API를 **`/api`(상대경로)**로 (같은 도메인이라 CORS 없음) |
| `FE/.dockerignore` | `node_modules`·`dist`·로컬 env 제외 (빌드 빠르게) |
| `docker-compose.prod.yml`의 `frontend` | **docker에 FE 등록** (이게 있어야 컨테이너가 뜬다) |
| `Caddyfile` catch-all | `/`는 frontend로, `/api`·`/ws`·이미지·영상은 backend/각자로 |

## ⚠️ 실제로 겪은 문제 3가지 (핵심)

### 1. 파일만 있으면 안 뜬다 → compose에 등록해야 함
`FE/Dockerfile`이 서버에 있어도, `docker-compose.prod.yml`에 `frontend` 서비스가 **없으면** docker가 컨테이너를 안 만든다. → **compose에 등록**해야 뜬다.

### 2. Caddy가 새 설정을 안 읽는다 → Caddy 컨테이너 재시작 필요
- `docker compose up`은 **컨테이너 스펙(이미지·포트·볼륨)이 바뀔 때만** 재시작한다. `depends_on` 추가나 **Caddyfile 내용 변경은 감지 못 함** → Caddy가 옛 라우팅 유지.
- 게다가 Caddyfile은 **bind mount(파일 단위)** 라, 배포(rsync)가 파일을 **새 inode로 교체**하면 컨테이너는 **옛 파일에 묶여 있어** `caddy reload`로도 새 내용을 못 읽는다.
- **해결: `docker restart vintib-caddy`** (현재 파일을 다시 마운트 + 새로 읽음).
- **근본 해결(TODO)**: 배포 스크립트(`deploy.sh`)에 "Caddyfile 바뀌면 caddy 재시작" 넣기 → 매번 수동으로 안 하게. (인프라 담당에게 요청)

### 3. healthcheck가 `localhost`로 붙어 unhealthy
nginx는 IPv4로만 듣는데 healthcheck가 `localhost`→IPv6(`::1`)로 붙어 실패 → 컨테이너는 멀쩡한데 표시만 `unhealthy`.
→ **해결: healthcheck를 `127.0.0.1`로** (`docker-compose.prod.yml`).

## 확인 방법

- 브라우저: `https://i15a108.p.ssafy.io` → 우리 화면 뜨면 성공
- `/healthz` → `ok` (FE nginx 응답), `/api/lives` → 200 (백엔드 정상)

## 한 줄 교훈

> **"파일 만들기 → docker에 등록 → 배포 → (Caddy 재시작)"** 네 단계가 다 돼야 뜬다.
> 파일만 있거나 compose 등록만으론 안 뜬다.
