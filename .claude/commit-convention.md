# 커밋 컨벤션

출처: Notion `프로/공통PJT/Wiki` > "코딩 컨벤션" (Git 브랜치 전략 및 협업 컨벤션, 4장). 원본이 수정되면 이 문서도 함께 갱신할 것.

## Claude 준수 사항 (하드 룰)

- **절대 직접 push하지 않는다.** 로컬 커밋까지만 수행하고, 원격 브랜치(`main`/`develop-*`/`feature/*` 등 어디든)로의 push는 항상 사용자가 직접 실행한다.
- **커밋 메시지에 Claude를 Co-Authored-By로 추가하지 않는다.**

## 커밋 메시지 형식

```
[<JIRA-KEY>] <type>: <subject>
```

- 이슈 키는 대괄호로 감싸 맨 앞에 위치 (JIRA가 이슈 키를 인식하는 표준 패턴)
- subject는 한글 기준 50자 이내
- body는 작성하지 않는다.

### type

| type | 의미 |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `style` | 코드 포맷팅, 세미콜론 등 (로직 변경 없음) |
| `refactor` | 리팩토링 (기능 변화 없음) |
| `test` | 테스트 코드 추가/수정 |
| `chore` | 빌드, 설정, 패키지 매니저 등 |

### 예시

```
[S15P11A108-23] feat: 카카오 로그인 API 연동
[S15P11A108-31] fix: 장바구니 수량 0일 때 삭제 안 되는 버그 수정
[S15P11A108-12] docs: 실행 방법 섹션 추가
```

## 관련 브랜치/MR 규칙 (요약)

- 브랜치: `feature/{JIRA이슈번호}-{작업내용}` (예: `feature/108-login-api`), `hotfix/{이슈번호}-{작업내용}`
- `main`, `develop-*`는 직접 커밋 금지 — 반드시 MR로만 반영
- MR은 리뷰어 2인 이상 승인 필요, 병합 방식은 Merge
- MR 템플릿: `.gitlab/merge_request_templates/Default.md` — GitLab에서 새 MR 생성 시 자동 적용됨.
  구성: 작업 내용 / 관련 이슈(JIRA 키) / 변경 사항(체크리스트) / 테스트(선택)
- 자세한 브랜치 전략·MR 템플릿·리뷰 규칙은 Notion 원본 문서 참고