# DB 이름 기본값 변경 (vintage_auction → vintib)

- **요청자 파트**: BE
- **대상 파트**: AI

## 배경/이유

DB 이름을 `vintib`로 확정했다. 공유 인프라(`docker-compose.yml`, `.gitlab-ci.yml`, 루트·BE `.env.example`)와 BE `application.yml`은 모두 반영을 마쳤는데, AI 쪽 기본값만 `vintage_auction`으로 남아 있다. 같은 PostgreSQL 인스턴스를 공유하므로 값이 어긋나면 AI 서비스가 없는 DB로 붙는다.

## 요청 내용

아래 두 곳의 기본값을 `vintib`로 바꿔주세요.

- `AI/.env.example` — `DB_NAME`
- `AI/config.py` — `Settings.db_name`

두 값 모두 환경변수 `DB_NAME`이 없을 때만 쓰이는 폴백이다. compose로 띄우면 `docker-compose.yml`이 `DB_NAME`을 주입하므로 실제 동작은 이미 `vintib`를 따른다. 다만 로컬에서 컨테이너 없이 FastAPI를 직접 실행할 때 폴백이 걸리므로 맞춰두는 편이 안전하다.

## 참고

- 기존 PostgreSQL 볼륨에는 `vintage_auction` DB만 있다. 볼륨을 지우지 않고 이름만 바꾸면 접속이 실패하므로, 로컬은 `CREATE DATABASE vintib` 또는 볼륨 재생성이 필요하다.
