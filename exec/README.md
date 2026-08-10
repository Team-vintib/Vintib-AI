# exec — 포팅 매뉴얼 제출 폴더

| 파일 | 내용 |
| --- | --- |
| `01_빌드_및_배포_매뉴얼.md` | 사용 제품/버전, 빌드 환경변수, 배포 특이사항, DB 접속정보가 정의된 파일 목록 |
| `02_외부_서비스_정보.md` | 프로젝트에서 사용하는 외부 서비스 가입·발급 정보 |
| `03_db_dump_vintib_YYYYMMDD.sql` | 운영(EC2) DB `vintib`의 최신 덤프, 개인정보 익명화 완료 (plain SQL, `pg_dump --no-owner --no-privileges`) |
| `04_시연_시나리오.md` | 최종 발표 시연 순서에 따른 화면별·조작별 상세 시나리오 |

소스코드는 이 폴더에 추가로 올리지 않는다(GitLab 소스클론으로 충분).

## DB 덤프 복원 방법

```bash
# 새 DB에 복원하는 경우 (예: 로컬 재현)
createdb -U postgres vintib_restore
psql -U postgres -d vintib_restore -f 03_db_dump_vintib_YYYYMMDD.sql

# 또는 docker compose로 띄운 postgres 컨테이너에 바로 흘려넣기
cat 03_db_dump_vintib_YYYYMMDD.sql | docker exec -i vintib-postgres psql -U postgres -d vintib
```

## 개인정보 익명화

운영 DB를 직접 커밋하지 않는다. EC2에서 운영 DB(`vintib`)를 임시 복제 DB(`vintib_sanitize`)로
복사한 뒤, 그 복제본에서만 아래 컬럼을 규칙적인 더미 값으로 치환하고 복제본을 덤프·삭제하는
방식으로 만들었다 — **운영 DB 자체는 read-only 접근만 했고 수정하지 않았다.**

| 테이블 | 익명화한 컬럼 |
| --- | --- |
| `member` | `email`, `name`, `nickname`, `phone_number`, `address`, `detail_address`, `postal_code`, `password`, `google_id`, `description`, `profile_image_url`, `cover_image_url` |
| `business_info` | `business_name`, `business_number`, `certificate_key`, `representative_name` |
| `invoice` | `business_name`, `business_number`, `representative_name` |
| `order_shipment` | `address1`, `address2`, `recipient_name`, `recipient_phone`, `zipcode`, `tracking_number` |
| `withdrawal_account` | `account_holder_name`, `account_number` |

값은 PK(`id`/`member_id`/`order_id`)에서 파생한 규칙적인 더미 값(`user{id}@example.com`,
`010-0000-{4자리}` 등)이라 행 간 구분·참조 관계는 그대로 유지된다. 그 외 테이블(상품·경매·
채팅·라이브 등)은 원본 데이터를 그대로 유지했다 — 개인 식별 정보가 없다고 판단했다.

⚠️ 위 목록 밖의 자유 텍스트 필드(채팅 메시지 등)는 익명화하지 않았다. 사용자가 채팅에 개인
정보를 직접 입력한 경우까지는 걸러내지 못하므로, 배포 전 육안 확인을 권장한다.

## 채팅 욕설 제외

`chat_message.content`를 전수 검사해 욕설·비속어가 담긴 행 4건(id 145, 146, 148, 198)을
덤프에서 완전히 삭제했다(치환이 아니라 행 자체 제거 — `is_blocked` 값과 무관하게 실제 내용
기준으로 걸러냈다). 나머지 277건은 원본 그대로다. `chat_message.id`를 FK로 참조하는 다른
테이블이 없어 삭제로 인한 참조 무결성 문제는 없다.