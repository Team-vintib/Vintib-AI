# JY012 WebRTC 미디어를 포트 80으로 (SSAFY 방화벽 우회)

## 배경/목표

라이브 영상이 join 직후 끊긴다(FE 요청 `028`). 조사 결과 **SSAFY 상위 방화벽이 TCP
22·80·443·8989 외에는 전부 막는다.** LiveKit 미디어 포트(UDP 7885 / TCP 7881)가 인스턴스에
도달하지 못해 ICE 가 성립하지 않는 것이 원인이다.

### 측정으로 확인한 것

| 확인 | 결과 |
| --- | --- |
| `NODE_IP` | `43.201.54.59` 공인 IP 정상. 로컬 후보도 정확히 광고됨 |
| UFW | `7885/udp`·`7881/tcp` **이미 허용돼 있었다** |
| 호스트 리슨 | `ss` 로 두 포트 모두 LISTEN 확인 |
| tcpdump | 나가는 패킷만 48개, **들어오는 패킷 0개** |
| LiveKit 로그 | `connectionType: "unknown"`, `removing participant without connection` |
| 외부 포트 스캔 | 22·80·443·8989 → 열림 / **7881 → 막힘** |
| UDP 443 프로브 | 12개 발신, **0개 도달** — UDP 는 전 포트 차단 |

**서버 버전은 원인이 아니다.** 로그에 `protocol: 17` 수락이 찍혀 있어 1.9.1 이 2.21 클라이언트를
정상 처리했다. `/rtc/v1` 404 → `/rtc` 폴백도 제대로 동작했다.

`BE/docs/infra/ec2.md` 의 "Docker publish 는 iptables 를 직접 조작해 UFW 를 우회하므로 외부에
열린다"는 서술은 **호스트 방화벽 기준에서만 맞고, 상위 방화벽 앞에서는 무의미했다.** 이 문서도
함께 고친다.

## 작업 내용

**열려 있는 포트 중 미디어에 내줄 수 있는 것은 80 하나뿐이다.** 22 는 SSH, 443 은 Caddy(웹·API·
시그널링), 8989 는 SSAFY Gerrit 이라 건드릴 수 없다. 그래서 **LiveKit TCP 미디어를 80 으로 옮기고
Caddy 를 80 에서 내린다.**

### 왜 컨테이너 안에서도 80 이어야 하는가

LiveKit 은 **자기 설정의 `tcp_port` 값을 그대로 ICE 후보로 광고한다**(로그의
`tcp4 host 43.201.54.59:7881` 이 그 증거다). 호스트만 `80:7881` 로 매핑하면 광고는 7881 로 나가
막힌 포트를 알려주게 된다. 1.9.x 에는 "광고용 외부 포트" 설정이 없어 **설정값 자체를 80 으로
바꾸고 `80:80` 으로 발행**해야 한다.

### Caddy 를 80 에서 내리는 대가

- `http://` → `https://` 자동 리다이렉트가 사라진다. 주소를 직접 치는 사용자는 붙지 못한다
- ACME 챌린지가 HTTP-01 을 못 쓴다 → **TLS-ALPN-01(443)** 로 명시 전환한다.
  그대로 두면 갱신 시점(만료 30일 전)에 조용히 실패해 **인증서가 만료되고 사이트가 통째로 죽는다**

### UDP 는 어떻게 되나

여전히 막혀 있어 쓸 수 없다. LiveKit 은 UDP 후보도 함께 광고하지만 클라이언트가 실패한 뒤 TCP 로
넘어간다 — 연결이 조금 늦어질 뿐 성립한다. UDP 를 끄는 설정은 넣지 않는다(로컬 개발은 UDP 가
정상 동작하고, SSAFY 가 나중에 열어 줄 여지도 남긴다).

**TCP 미디어는 UDP 보다 지연·재전송에 불리하다.** 이건 회피가 아니라 감수하는 트레이드오프다 —
상위 방화벽을 우리가 못 여는 이상 대안이 없다.

## 구현 목록

- [ ] `infra/livekit/livekit.yaml` — `rtc.tcp_port` 를 `80` 으로. 이유를 주석에 남긴다
- [ ] `docker-compose.prod.yml` — livekit 발행을 `80:80` 으로. 기존 `7881:7881` 제거,
      `7885:7885/udp` 는 유지(상위에서 막히지만 설정 일관성)
- [ ] `docker-compose.prod.yml` — caddy 발행에서 `80:80` 제거
- [ ] `infra/caddy/Caddyfile` — 전역 옵션 `auto_https disable_redirects`,
      사이트 블록에 `tls { issuer acme { disable_http_challenge } }`
- [ ] `docker-compose.override.yml`(로컬) — livekit `80:80` 으로 맞춰 설정 단일화
- [ ] `BE/docs/infra/ec2.md` — 포트 표·"UFW 우회" 서술 정정, 상위 방화벽 제약 명시
- [ ] `infra/ec2/setup-ufw-media.sh` — 80/tcp 안내 추가(이미 열려 있어 규칙 변경은 불필요)
- [ ] FE 인계 문서 — **FE 코드 변경 없음**을 명시(시그널링 443 그대로, 미디어는 ICE 로 자동)

## 배포 전 확인

- [ ] `docker exec vintib-livekit id` — root 여야 80 을 바인딩할 수 있다. 아니면
      `user: root` 또는 `cap_add: NET_BIND_SERVICE` 를 추가해야 한다
- [ ] 배포 시 Caddy 가 80 을 놓은 뒤 LiveKit 이 잡아야 한다. 한 번에 안 되면
      `docker compose up -d --force-recreate caddy livekit`

## 검증

- [ ] 외부에서 `Test-NetConnection <IP> -Port 80` → True
- [ ] tcpdump 에 **양방향** 패킷(지난번엔 나가는 것만 48개)
- [ ] 브라우저에서 영상 표시, 콘솔에 `disconnected` 없음
- [ ] `docker logs vintib-caddy` 에 ACME 오류 없음, HTTPS 정상
