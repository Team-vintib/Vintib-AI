# EC2 세팅 (S15P11A108-297)

## 배경/목표

팀 EC2 1대(`i15a108.p.ssafy.io`, 43.201.54.59)를 전체 백엔드 런타임 + CI/CD 러너 겸용으로 쓸 수 있게 기반을 완성한다. 이 프로젝트의 AWS/EC2 작업은 전부 이 티켓으로 모은다.

## 현재 상태 (2026-07-23 SSH 실측)

**⚠️ 이 EC2에는 SSAFY가 제공한 Gerrit 코드리뷰 서버가 이미 돌고 있다.** 8988/8989(Apache httpd)/29418 포트가 그것이며 UFW의 `8989` 규칙도 Gerrit 것이다. **절대 건드리지 않는다.**

| 항목 | 상태 | 이번 작업 |
| --- | --- | --- |
| Ubuntu 24.04 / 4 vCPU / 15Gi RAM / 309GB | ✅ | — |
| Docker 29.6.2 + Compose v5.3.1 | ✅ 설치됨 (ubuntu가 sudo 없이 docker 실행 가능) | — |
| passwordless sudo | ✅ | — |
| **GitLab Runner 19.2.0** | ✅ **설치+등록+online** (docker executor, `ip-172-26-2-120`, verify=valid, 캐시 볼륨 존재→실행 이력 있음) | 파이프라인 1회 성공만 확인 |
| UFW active | ✅ 22 / 443 / 8989(Gerrit) 개방 | 80 추가, OpenVidu 포트는 보류 |
| swap | ❌ 0B | **4GB 생성** |
| 앱 컨테이너(postgres/redis/backend/ai) | ❌ 미기동 | **compose로 기동** |
| 리버스 프록시 + TLS | ❌ 없음 (443 UFW 열려 있으나 리스닝 프로세스 없음, caddy/nginx 부재) | **standalone Caddy로 구축** |
| 배포 디렉터리 규약 | ❌ 없음 | `/home/ubuntu/vintib/` 규약 |
| OpenVidu v3 | ❌ 없음 | **이번 범위 아님** (로드맵상 2주차 초, 별도) |

**결론: 티켓 원안보다 범위가 크게 줄었다.** Docker·Compose·Runner 설치가 이미 끝나 있다. 남은 핵심은 swap / TLS 프록시 / compose 기동 / 검증이다.

## 작업 내용

레포에 **재현 가능한 스크립트·설정으로 남기고**, 그 스크립트를 EC2에서 실행한다. 손으로 명령만 치면 재해 복구·인수인계가 안 된다. 서버 변경은 전부 사용자 승인 후 실행한다.

- **swap**: `/swapfile` 4GB, `swappiness=10`, `/etc/fstab` 등록(재부팅 유지)
- **UFW**: 80/tcp 추가(Let's Encrypt HTTP-01 + HTTP→HTTPS 리다이렉트). 기존 22/443/8989 규칙은 손대지 않는다
- **리버스 프록시(Caddy 컨테이너)**: `i15a108.p.ssafy.io` TLS 자동 발급(Let's Encrypt), `/` → `backend:8080` 프록시. compose에 `prod`에서만 뜨는 프록시 서비스로 추가하고 `vintib-net`에 붙인다
- **앱 기동**: 레포를 `/home/ubuntu/vintib/`에 클론, `.env` 작성(운영 비밀번호), `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- **검증**: 4개 컨테이너 healthcheck / `ss -tlnp`로 DB·Redis·FastAPI 미노출 확인 / 외부에서 `https://i15a108.p.ssafy.io/api/health` 200 / `ufw status` active
- **문서화**: `BE/docs/infra/ec2.md` — 개방 포트, 디렉터리 규약, 재현 절차, Gerrit 공존 주의

## 구현 목록

- [ ] `infra/ec2/setup-swap.sh` — swap 4GB (멱등)
- [ ] `infra/ec2/setup-ufw.sh` — 80/tcp 추가 (기존 규칙 보존, 멱등)
- [ ] `docker-compose.prod.yml`에 Caddy 리버스 프록시 서비스 추가 + `infra/caddy/Caddyfile`
- [ ] `backend`를 prod에서 호스트 포트 미바인딩으로 전환 (Caddy만 80/443 노출, backend는 vintib-net 내부로)
- [ ] EC2에 레포 클론 + `.env` 작성 후 compose 기동
- [ ] 검증: healthcheck 4/4, 포트 노출 검사, 외부 HTTPS 200, ufw active
- [ ] GitLab 샘플 파이프라인 1회 성공 확인
- [ ] `BE/docs/infra/ec2.md` 문서화

## 결정 사항 (2026-07-23 사용자 승인)

1. **TLS**: 독립 Caddy 컨테이너로 지금 세운다. OpenVidu(2주차)와는 그때 정합.
2. **backend 노출**: prod에서 backend를 호스트에 바인딩하지 않고 vintib-net 내부 전용으로 전환. Caddy만 80/443 노출.
3. **운영 DB 비밀번호**: 사용자가 EC2 `.env`에 직접 입력. 레포·커밋·대화에 값을 남기지 않는다.
4. **실행**: 단계별 승인받고 이 세션에서 실행 (swap → UFW → 프록시/기동 순).
