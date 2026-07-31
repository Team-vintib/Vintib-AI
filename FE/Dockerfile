# FE 배포 이미지 — 멀티스테이지 (node 빌드 → nginx 서빙)
# 계획: docs/plans/FE/HS020-fe-deploy.md
# Caddy 뒤에서 frontend:80 으로 서빙된다 (호스트 포트는 열지 않음).

# ---- 1단계: 빌드 ----
# CI(fe-test)와 동일한 node:22-alpine 로 맞춘다.
FROM node:22-alpine AS builder
WORKDIR /app

# 의존성 먼저 설치 — package.json 만 먼저 복사해 레이어 캐시를 활용한다.
COPY package*.json ./
RUN npm ci

# 소스 복사 후 프로덕션 빌드.
# 타입체크(vue-tsc)는 CI(fe-test)가 담당하므로, 이미지 빌드는 build-only(vite build)로
# 빠르게 끝낸다. .env.production 이 자동 적용되어 API 주소가 /api 로 박힌다.
COPY . .
RUN npm run build-only

# ---- 2단계: 서빙 ----
FROM nginx:1.27-alpine

# 커스텀 nginx 설정 (SPA fallback / healthz / 캐시 정책)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드 산출물(dist)만 복사한다. node 는 최종 이미지에 포함되지 않아 작고 안전하다.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
