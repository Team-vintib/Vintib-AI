#!/bin/sh
# develop-BE 병합 시 EC2 자동 배포 (S15P11A108-262)
#
# GitLab CI 의 deploy 잡에서 실행된다. 잡 컨테이너에는 아래가 마운트되어 있다.
#   /var/run/docker.sock          호스트 도커 데몬
#   /home/ubuntu/vintib           배포 디렉터리 (호스트와 동일 경로)
# 동일 경로로 마운트하는 이유: compose 의 bind mount(Caddyfile 등)는 데몬이 있는
# 호스트 파일시스템 기준으로 해석되므로, 잡 안에서의 경로와 어긋나면 안 된다.
#
# 흐름: 코드 동기화 → .env 생성 → 빌드·기동 → 헬스체크 → 실패 시 직전 이미지로 롤백
set -eu

DEPLOY_DIR=/home/ubuntu/vintib
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib"
HEALTH_TIMEOUT=180
# 브라우저가 실제로 여는 주소. presigned·공개 이미지 URL 이 이 값으로 서명된다.
# infra/caddy/Caddyfile 의 사이트 주소와 반드시 같아야 한다 (서명에 Host 가 포함됨).
PUBLIC_ORIGIN=https://i15a108.p.ssafy.io

log() { echo "[deploy] $*"; }

# ---------- 0. 직전 배포 태그 기록 (롤백용) ----------
PREVIOUS_TAG=""
if [ -f "$DEPLOY_DIR/.env" ]; then
    PREVIOUS_TAG=$(grep '^IMAGE_TAG=' "$DEPLOY_DIR/.env" 2>/dev/null | cut -d= -f2 || true)
fi
log "직전 태그: ${PREVIOUS_TAG:-(없음)} → 새 태그: $IMAGE_TAG"

# ---------- 1. 코드 동기화 ----------
# .env 는 아래에서 새로 만들고, _disabled/ 는 운영 안전장치라 보존한다.
log "코드 동기화 → $DEPLOY_DIR"
rsync -a --delete \
    --exclude '.git' \
    --exclude '.env' \
    --exclude '_disabled' \
    "$CI_PROJECT_DIR/" "$DEPLOY_DIR/"

# 운영 디렉터리에 override 가 있으면 -f 없이 기동했을 때 DB·Redis 가 노출된다.
# 동기화로 다시 들어왔을 수 있으므로 격리한다.
if [ -f "$DEPLOY_DIR/docker-compose.override.yml" ]; then
    mkdir -p "$DEPLOY_DIR/_disabled"
    mv "$DEPLOY_DIR/docker-compose.override.yml" \
       "$DEPLOY_DIR/_disabled/docker-compose.override.yml.disabled"
    log "override 파일 격리함"
fi

# ---------- 2. .env 생성 (GitLab CI/CD Variables) ----------
# ⚠️ DB_PASSWORD 는 PostgreSQL 볼륨을 처음 만들 때의 값과 같아야 한다.
#    값을 바꾸면 볼륨을 지우거나 ALTER USER 를 해야 백엔드가 붙는다.
# 운영 비밀번호는 PROD_DB_PASSWORD 로 받는다. DB_PASSWORD 라는 이름을 쓰면
# 프로젝트 변수가 be-test 의 테스트용 DB_PASSWORD 까지 덮어써 테스트가 깨진다.
#
# ⚠️ MINIO_ROOT_USER/PASSWORD 도 DB 와 똑같은 함정이 있다. MinIO 는 이 값을 minio-data
#    볼륨을 처음 만들 때의 값으로 굳히므로, 나중에 바꾸면 백엔드의 서명 검증이 전부
#    실패한다(고치려면 볼륨을 지워야 하고 = 업로드된 이미지가 전부 사라진다).
#    이름에 PROD_ 접두사를 쓰는 이유도 DB 와 같다 — be-test 잡의 MinIO 서비스
#    컨테이너가 MINIO_ROOT_USER 를 job 변수로 쓰는데, 프로젝트 변수가 그걸 이긴다.

# heredoc 확장 전에 필수 변수를 먼저 전부 검사한다.
# 이유 두 가지:
#   1) set -u 만 믿으면 위에서부터 하나씩 터져, CI/CD Variables 를 한 번에 못 채운다.
#   2) `cat > .env` 는 리다이렉션이 먼저 처리되므로 확장이 실패하면 운영 .env 가
#      빈 파일로 남는다 → 다음 배포의 롤백 기준 태그(PREVIOUS_TAG)까지 사라진다.
REQUIRED_VARS="DB_NAME DB_USERNAME PROD_DB_PASSWORD IMAGE_TAG CORS_ALLOWED_ORIGINS
PROD_MINIO_ROOT_USER PROD_MINIO_ROOT_PASSWORD PROD_MAIL_USERNAME PROD_MAIL_PASSWORD"

missing=""
for name in $REQUIRED_VARS; do
    eval "value=\${$name:-}"
    [ -n "$value" ] || missing="$missing $name"
done
if [ -n "$missing" ]; then
    log "!! 필수 CI/CD Variable 이 비어 있다:$missing"
    log "   GitLab → Settings → CI/CD → Variables 에서 등록한다."
    log "   (Protected 로 등록하려면 develop-BE 도 protected 브랜치여야 한다)"
    exit 1
fi

log ".env 생성"
umask 077
# 임시 파일에 쓴 뒤 교체한다. 중간에 실패해도 기존 .env 가 살아남는다.
cat > "$DEPLOY_DIR/.env.tmp" <<ENV
DB_NAME=${DB_NAME}
DB_USERNAME=${DB_USERNAME}
DB_PASSWORD=${PROD_DB_PASSWORD}
SPRING_PROFILES_ACTIVE=prod
SERVER_PORT=8080
IMAGE_TAG=${IMAGE_TAG}
CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
MINIO_ROOT_USER=${PROD_MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${PROD_MINIO_ROOT_PASSWORD}
MAIL_USERNAME=${PROD_MAIL_USERNAME}
MAIL_PASSWORD=${PROD_MAIL_PASSWORD}
AWS_S3_PUBLIC_ENDPOINT=${PUBLIC_ORIGIN}
ENV
mv "$DEPLOY_DIR/.env.tmp" "$DEPLOY_DIR/.env"

cd "$DEPLOY_DIR"

# ---------- 3. 빌드 및 기동 ----------
log "이미지 빌드 (태그 $IMAGE_TAG)"
$COMPOSE build

log "서비스 교체"
$COMPOSE up -d

# ---------- 4. 헬스체크 ----------
# backend 가 healthy 가 되어야 배포 성공으로 본다.
log "헬스체크 (최대 ${HEALTH_TIMEOUT}초)"
elapsed=0
healthy=""
while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    status=$(docker inspect -f '{{.State.Health.Status}}' vintib-backend 2>/dev/null || echo "none")
    if [ "$status" = "healthy" ]; then
        healthy="yes"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
done

# ---------- 5. 실패 시 롤백 ----------
if [ -z "$healthy" ]; then
    log "!! 헬스체크 실패 (backend 상태: ${status:-unknown})"
    docker logs --tail 50 vintib-backend 2>&1 || true

    if [ -n "$PREVIOUS_TAG" ] && [ "$PREVIOUS_TAG" != "$IMAGE_TAG" ]; then
        log "직전 이미지($PREVIOUS_TAG)로 롤백 시도"
        sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$PREVIOUS_TAG/" "$DEPLOY_DIR/.env"
        $COMPOSE up -d
        log "롤백 완료 — 배포는 실패로 처리한다"
    else
        log "롤백할 직전 이미지가 없다"
    fi
    exit 1
fi

log "배포 성공 — backend healthy"
$COMPOSE ps

# ---------- 6. 디스크 정리 ----------
# 러너와 런타임이 동거해 이미지가 빠르게 쌓인다.
# dangling 이미지만 지우므로 롤백용 직전 태그 이미지는 남는다.
log "dangling 이미지 정리"
docker image prune -f >/dev/null 2>&1 || true
