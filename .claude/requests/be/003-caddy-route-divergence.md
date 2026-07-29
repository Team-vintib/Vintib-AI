# EC2 Caddyfile이 develop-BE/develop-AI 사이에서 갈라져 있음 — 병합 필요

- **요청자 파트**: AI
- **대상 파트**: BE / 인프라
- **관련 티켓**: `S15P11A108-444` (chat_rag 생성기)
- **상태**: 요청

## 배경

`S15P11A108-444` 로컬 검증 후 EC2에서 실 서버 테스트를 시도하다가(`~/vintib`) 발견한
문제입니다. `infra/caddy/Caddyfile`은 AI/BE 양쪽이 같이 쓰는 공유 파일인데, **두 브랜치의
버전이 서로 다른 라우팅 규칙을 갖고 있습니다.**

- `develop-AI` 쪽 `Caddyfile`: `/ai/*`, `/results/*`, `/chat/*` → `ai:8000`, 나머지 →
  `backend:8080`.
- `develop-BE` 쪽 `Caddyfile`(EC2에서 직접 `cat`으로 확인): MinIO 라우트(`/vintib-public/*`,
  `/vintib-private/*`)만 추가돼 있고 **`/ai/*`·`/results/*`·`/chat/*`가 전부 빠져 있습니다.**

자동배포가 `develop-BE` 푸시로만 트리거되고 `~/vintib`를 그 브랜치 기준으로 덮어쓰는 구조라,
BE가 배포할 때마다 AI 쪽 라우팅이 통째로 사라집니다. 실제로 `/chat/*` 라우트를 추가하고
Caddy를 재시작해 확인까지 했는데, 그 이후 BE 배포가 한 번 더 돌면서 다시 사라진 걸
확인했습니다(그때는 수동으로 두 버전을 합쳐 임시로 복구, 커밋은 안 함 — 다음 배포 때
다시 사라집니다).

## 요청 내용

`infra/caddy/Caddyfile`을 **두 브랜치 모두의 라우트를 합친 하나의 버전**으로 만들어서 양쪽
`develop-*`에 반영해 주세요. AI 쪽 라우트(`/ai/*`, `/results/*`, `/chat/*` → `ai:8000`)는
로컬 `develop-AI` 기준 그대로 두시면 되고, 여기에 BE의 MinIO 라우트를 추가하면 됩니다.

더불어, 이 파일이 공유 파일인 이상 한쪽 브랜치만 건드리면 같은 문제가 재발합니다. 배포
파이프라인이 `main`처럼 양쪽이 합쳐진 브랜치를 기준으로 돌게 하거나, 최소한 이 파일만큼은
수정 시 다른 파트에 공유하는 규칙을 두는 걸 검토해 주시면 좋겠습니다.

## 참고

- 확인 경로: EC2 `~/vintib/infra/caddy/Caddyfile` 직접 `cat`, `docker compose ps`로
  `vintib-minio` 정상 기동 확인.
- 같은 세션에서 `~/vintib` 체크아웃 자체가 git 트리와 디스크 상태가 어긋나 있는 손상도
  발견했습니다(`git ls-tree`엔 `AI/app`이 있는데 디스크엔 없고, 대신 오래된 `main.py`가
  남아 있음). 새로 클론한 `~/vintib-ai-test`는 정상이었습니다 — `~/vintib`를 한 번 정리하고
  다시 배포해 보시는 걸 권장드립니다. 이건 저희가 직접 손대지 않았습니다(다른 파트 작업 디렉터리라).
