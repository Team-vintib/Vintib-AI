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

- **OpenVidu v3 (WebRTC 미디어 서버)** — 로드맵상 2주차 초. 설치 시 TURN/미디어 UDP 포트를 UFW에 추가하고, 이 Caddy와 정합(또는 OpenVidu 내장 Caddy로 일원화)한다.
- **git 기반 자동 배포(CD)** — `-262`. 현재는 작업트리 tarball 수동 배치이며, 러너가 `develop-BE` 병합 시 `/home/ubuntu/vintib`를 git으로 갱신·재기동하도록 파이프라인을 구성한다.
