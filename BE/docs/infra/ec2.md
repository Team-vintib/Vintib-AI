# EC2 운영 환경 (S15P11A108-297)

팀 EC2 1대에 전체 백엔드 런타임과 CI/CD 러너를 올린 구성. 이 프로젝트의 AWS/EC2 관련 사항은 전부 여기에 모은다.

- 호스트: `i15a108.p.ssafy.io` (43.201.54.59)
- OS: Ubuntu 24.04 LTS / 4 vCPU / 15GiB RAM / 309GB disk
- 접속: `ssh -i I15A108T.pem ubuntu@i15a108.p.ssafy.io` (passwordless sudo)

## ⚠️ 이 서버에는 SSAFY Gerrit이 함께 돈다

`8988` / `8989`(Apache httpd) / `29418`(Gerrit SSH) 포트는 **SSAFY가 제공한 Gerrit 코드리뷰 서버**다. UFW의 `8989` 규칙도 Gerrit 것이다.

**우리 서비스가 아니므로 절대 건드리지 않는다.** 포트를 추가할 때 8988/8989/29418을 점유하지 않는다.

## 개방 포트

| 포트 | 용도 | 노출 |
| --- | --- | --- |
| 22 | SSH | 공개 (UFW) |
| 80 | HTTP → HTTPS 리다이렉트 + Let's Encrypt ACME | 공개 (UFW) |
| 443 | HTTPS (Caddy TLS 종단) | 공개 (UFW) |
| 7881 | WebRTC 미디어 TCP 폴백 (LiveKit) | 공개 (**Docker publish**) |
| 7885/udp | WebRTC 미디어 UDP mux (LiveKit) | 공개 (**Docker publish**) |
| 8989 | **Gerrit (SSAFY, 건드리지 말 것)** | 공개 (UFW) |

**앱 내부 포트(8080 backend / 5432 postgres / 6379 redis / 8000 ai)는 호스트에 노출하지 않는다.** Docker는 포트 publish 시 iptables를 직접 조작해 UFW를 우회하므로, 이들을 publish하면 UFW와 무관하게 외부에 뚫린다. 전부 `vintib-net` 내부 통신 전용이며, 외부 접근은 Caddy(443)를 통해서만 backend로 들어간다.

```
브라우저 ──HTTPS/443──▶ Caddy ──vintib-net──▶ backend:8080
                                              ├── postgres:5432
                                              ├── redis:6379
                                              └── ai:8000
```

## 디렉터리 규약

| 경로 | 내용 |
| --- | --- |
| `/home/ubuntu/vintib/` | 배포된 레포 (compose 실행 위치) |
| `/home/ubuntu/vintib/.env` | 운영 환경변수 (권한 600, **git 미추적**, DB 비밀번호 포함) |
| `/home/ubuntu/vintib/_disabled/` | 운영에서 병합되면 안 되는 파일 격리 (override 등) |
| `/swapfile` | 4GB swap |

> `docker-compose.override.yml`은 운영 디렉터리에서 `_disabled/`로 격리해 두었다. 이 파일이 있으면 누군가 `-f` 없이 `docker compose up`만 쳤을 때 DB·Redis가 호스트에 노출된다. **운영 기동은 반드시 `-f`를 명시한다.**

## 세팅 내역

이미 되어 있던 것(SSAFY 제공): Docker 29.6.2 + Compose v5.3.1, GitLab Runner 19.2.0(등록·online), UFW active(22/443/8989).

이번 -297에서 한 것:

| 항목 | 스크립트/설정 |
| --- | --- |
| swap 4GB (swappiness=10, fstab 등록) | [`infra/ec2/setup-swap.sh`](../../../infra/ec2/setup-swap.sh) |
| UFW 80/tcp 추가 (기존 규칙 보존) | [`infra/ec2/setup-ufw.sh`](../../../infra/ec2/setup-ufw.sh) |
| Caddy 리버스 프록시 + Let's Encrypt TLS | [`infra/caddy/Caddyfile`](../../../infra/caddy/Caddyfile), `docker-compose.prod.yml` |
| 앱 컨테이너 5종 기동 | `docker-compose.prod.yml` |

## 기동·재현 절차

```bash
# 1) 코드 배치 — /home/ubuntu/vintib/ 에 레포를 둔다
#    (현재는 작업트리 tarball로 배치. git 기반 자동 배포는 -262에서 구축)

# 2) 운영 .env 준비 — DB_PASSWORD는 직접 입력 (git·커밋에 남기지 않는다)
cd /home/ubuntu/vintib
read -rs -p 'DB password: ' P; echo
{ grep -v '^DB_PASSWORD=' .env; printf 'DB_PASSWORD=%s\n' "$P"; } > .env.tmp && mv .env.tmp .env && chmod 600 .env; unset P

# 3) 빌드 + 기동 — override가 병합되지 않도록 반드시 -f 명시
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4) 상태 확인
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

> ⚠️ DB 비밀번호는 PostgreSQL 볼륨의 **최초 생성 시점에만** 반영된다. 이미 `postgres-data` 볼륨이 있으면 `.env`의 비밀번호를 바꿔도 적용되지 않는다. 비밀번호를 바꾸려면 볼륨을 지우거나(데이터 삭제) 컨테이너 안에서 `ALTER USER`로 바꾼다.

## 검증 (완료조건)

```bash
# 컨테이너 상태 — postgres/redis/backend/ai/caddy 모두 healthy(caddy는 상태체크 없음)
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 외부 HTTPS — 200 + 유효 TLS
curl -sS https://i15a108.p.ssafy.io/api/health
#   → {"success":true,"data":{"backend":"UP","aiServer":"UP"},"error":null}

# 포트 노출 검사 — 0.0.0.0에는 22/80/443만, 5432/6379/8000/8080 없어야 정상
sudo ss -tlnp | grep -E ':(5432|6379|8000|8080)\b'   # 결과 없어야 함

# 방화벽
sudo ufw status        # active, 22/80/443/8989

# swap
swapon --show          # /swapfile 4G
```

2026-07-23 기준 위 전 항목 통과. Let's Encrypt 인증서 발급 완료(만료 자동 갱신, Caddy `caddy-data` 볼륨에 영속).

## 범위 밖 (후속 티켓)

- ~~**OpenVidu v3 (WebRTC 미디어 서버)**~~ — 아래 "WebRTC 미디어 서버" 절로 반영 완료(`-448`).

## 배포 흐름 (S15P11A108-27)

```
feat/*  →  develop-{BE,FE,AI}  →  main  →  자동 배포(EC2)
```

**배포 트리거는 `main` 하나다.** 파트별 `develop-*`를 각각 트리거로 걸면 안 된다.

### 파트 브랜치를 트리거로 걸면 안 되는 이유

`deploy.sh`는 트리거된 커밋 시점의 **저장소 전체**를 rsync한다. 파트 브랜치를 트리거로 걸면 **나중에 배포하는 쪽이 항상 상대 파트를 되돌린다.**

```
develop-FE 배포 → BE/ 도 develop-FE 시점 것으로 덮임 → BE 롤백
develop-BE 배포 → FE/ 도 develop-BE 시점 것으로 덮임 → FE 롤백
```

"서로 자주 머지하자"는 규칙으로는 못 막는다 — **양쪽이 서로를 포함하려면 두 브랜치가 같은 커밋이어야** 하기 때문이다. 파트가 셋이라 더 그렇다.

`main`은 이미 세 파트가 모이는 통합 브랜치이므로, 여기서 배포하면 어느 파트도 되돌아가지 않는다. 새 브랜치를 만들 필요도 없다.

### 배포하려면

각 파트는 `develop-*`까지 평소대로 진행하고, **배포 시점에 `develop-* → main` MR을 올린다.** main 병합이 곧 배포다.

> ⚠️ CI/CD Variables를 **Protected**로 등록했다면 `main`이 **protected 브랜치**여야 한다. 아니면 배포 잡에서 변수가 비어 `필수 CI/CD Variable 이 비어 있다`로 멈춘다.

### FE 컨테이너 (진행 중)

FE는 `frontend`(nginx) 컨테이너로 배포하고 Caddy가 catch-all을 FE로 보낸다. **`Caddyfile`의 백엔드 경로 명시는 이미 끝났고**(아래), `docker-compose.prod.yml`의 `frontend` 서비스는 `FE/Dockerfile`이 저장소에 들어온 뒤에 추가한다 — 없는 상태로 추가하면 `compose build`가 실패해 배포 잡이 통째로 깨진다.

**백엔드는 `/api` 밖에서도 서비스한다.** catch-all을 FE로 넘기기 전에 아래를 명시적으로 backend로 보내야 한다. `SecurityConfig`의 `PUBLIC_ENDPOINTS`와 같은 목록이므로 한쪽만 고치지 말 것.

| 경로 | 용도 |
| --- | --- |
| `/api/*` | REST |
| `/ws`, `/ws/*` | **STOMP** — 채팅·시청자 수·반응이 전부 여기 얹혀 있다 |
| `/actuator/*` | 헬스체크 |
| `/swagger-ui/*`, `/v3/api-docs` | **API 문서 (팀 전체가 쓴다)** |

`/api/*`와 `/ws`만 챙기면 **Swagger와 actuator가 조용히 죽는다.**

## WebRTC 미디어 서버 (S15P11A108-448)

### 공식 번들을 쓰지 않고 미디어 코어만 올린다

OpenVidu v3 Community 번들은 **자체 Caddy·Redis·MinIO·MongoDB·대시보드**를 함께 띄운다. 우리 환경에서는 대가가 크다.

| 문제 | 내용 |
| --- | --- |
| **443 충돌** | 번들 내장 Caddy가 443을 요구한다. 우리 Caddy가 이미 쓰고 있고 인증서도 거기 있다 |
| **중복** | Redis·MinIO를 이미 운영 중이다. 같은 것을 두 벌 돌릴 이유가 없다 |
| **메모리** | 현재 8.5GB(+러너 버스트 3GB) / 15GB. 번들은 4~6GB를 더 먹어 예산을 넘는다 |

**OpenVidu v3는 LiveKit 기반이라 미디어 코어(`livekit-server`)만 올려도 클라이언트(`livekit-client`)·서버 SDK·room 개념이 전부 동일하다.** 우리가 쓰는 것은 그 부분뿐이고, 번들이 더해주는 것은 관측·대시보드다. 그래서 `livekit-server` 단일 컨테이너로 간다(약 500MB).

> 나중에 STT용 오디오 추출이 필요하면 LiveKit Egress 컨테이너를 추가로 붙인다. 번들 전체를 되돌릴 필요는 없다.

### 시그널링은 기존 Caddy가, 미디어는 직접

**서브도메인을 쓸 수 없어**(SSAFY가 호스트 하나만 준다) 같은 도메인의 경로로 나눈다.

```
브라우저 ──wss://i15a108.p.ssafy.io/rtc──▶ Caddy(443) ──▶ livekit:7880   (시그널링)
브라우저 ──────────UDP 7885 / TCP 7881──────────────────▶ livekit        (미디어, 직통)
백엔드   ──http://livekit:7880/twirp/*──────────────────▶ livekit        (room 관리)
```

**미디어는 Caddy를 통과할 수 없다.** 리버스 프록시가 다룰 수 있는 HTTP가 아니라 브라우저와 서버가 직접 주고받는 UDP 스트림이기 때문이다. 그래서 이 두 포트만은 호스트에 publish한다.

> ⚠️ Docker는 publish 시 iptables를 직접 조작해 **UFW를 우회한다.** 즉 7885/7881은 UFW 규칙과 무관하게 외부에 열린다. **이건 실수가 아니라 의도다** — 시청자가 어디서든 붙어야 한다. `infra/ec2/setup-ufw-media.sh`로 UFW에도 규칙을 넣는 이유는 `ufw status`가 서버의 실제 개방 상태를 그대로 보여주게 하기 위해서다.

**미디어 포트는 단일 포트로 묶었다(UDP mux).** 기본값은 50000-60000 범위인데, 그러면 UFW에 만 개짜리 규칙이 생기고 Docker publish도 그만큼 느려진다. 우리 규모에서는 차이가 없다.

### ⚠️ `LIVEKIT_NODE_IP`를 반드시 채운다

컨테이너가 보는 IP는 사설 주소(`172.x`)다. 그대로 두면 **브라우저에 사설 IP를 ICE 후보로 알려 미디어 연결이 성립하지 않는다.** 증상이 고약하다 — **에러 없이 화면만 검게 나온다.**

설정 파일은 `use_external_ip: false`다. 켜면 기동 시 STUN으로 공인 IP를 조회하는데, 외부 UDP가 막힌 환경에서는 타임아웃되어 **서버가 아예 뜨지 않는다.** 그래서 자동 탐지 대신 `NODE_IP`로 공인 IP를 직접 알려준다.

`deploy.sh`가 `PROD_LIVEKIT_NODE_IP`를 필수 변수로 검사한다.

### ⚠️ UDP 버퍼를 키우지 않으면 영상이 끊긴다

기동 로그에 이 경고가 나오면 커널 UDP 버퍼가 부족한 것이다.

```
WARN  UDP receive buffer is too small for a production set-up
      {"current": 425984, "suggested": 5000000}
```

WebRTC는 UDP로 미디어를 나르므로 **버퍼가 작으면 트래픽이 몰릴 때 커널이 패킷을 버린다.** 시청자가 늘수록 심해지고, 애플리케이션 로그에는 아무것도 안 남아 원인을 찾기 어렵다. 호스트 커널 설정이라 컨테이너 안에서는 못 바꾼다.

```bash
bash infra/ec2/setup-udp-buffer.sh
sudo docker restart vintib-livekit
```

### `.env`는 `ubuntu` 계정으로 읽을 수 없다

배포 스크립트가 `umask 077`(600)로 만들고 **GitLab 러너 사용자 소유**다. 시크릿이 들어 있어 의도한 것이다. `docker compose` 명령은 `.env`를 읽으므로 **`sudo`를 붙여야 한다.**

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib ps
```

`docker logs`는 파일을 읽지 않아 `sudo` 없이 된다.

### 적용 절차

```bash
bash infra/ec2/setup-ufw-media.sh
bash infra/ec2/setup-udp-buffer.sh
sudo docker restart vintib-livekit
```

확인:

```bash
docker logs vintib-livekit          # nodeIP 가 공인 IP 인지 (사설 172.x 면 잘못됨)
sudo ss -ulnp | grep 7885
sudo ss -tlnp | grep 7881
curl -s https://i15a108.p.ssafy.io/rtc/validate?access_token=<토큰>   # success 면 정상
```

### 필요한 CI/CD Variables

| 변수 | 예시 |
| --- | --- |
| `PROD_OPENVIDU_API_KEY` | `openssl rand -hex 8` |
| `PROD_OPENVIDU_API_SECRET` | `openssl rand -base64 36` |
| `PROD_OPENVIDU_SERVER_URL` | `wss://i15a108.p.ssafy.io` |
| `PROD_LIVEKIT_NODE_IP` | EC2 공인 IP |
- **git 기반 자동 배포(CD)** — `-262`. 현재는 작업트리 tarball 수동 배치이며, 러너가 `develop-BE` 병합 시 `/home/ubuntu/vintib`를 git으로 갱신·재기동하도록 파이프라인을 구성한다.
