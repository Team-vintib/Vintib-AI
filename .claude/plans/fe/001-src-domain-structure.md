# FE src 도메인 폴더 구조 정리

## 배경/목표

기능정의서의 기능 ID prefix를 기준으로 프론트엔드 화면과 도메인 코드를 분리한다. 이후 회원가입을 포함한 각 화면 구현 시 같은 구조를 사용하도록 빈 폴더와 `.gitkeep`을 먼저 생성한다.

## 작업 내용

- `src/domains` 아래에 기능 ID prefix별 도메인 폴더를 만든다.
- 각 도메인은 `pages`, `components`, `api`, `types`, `constants` 하위 폴더를 동일하게 가진다.
- 공통 코드 위치로 `src/shared`를 만들고, 앱 조립 영역으로 `src/app`을 만든다.
- 빈 폴더가 Git에 유지되도록 각 폴더에 `.gitkeep`을 둔다.
- 실제 화면 구현 전에 구조 문서를 갱신한다.

## 구현 목록

- [x] `src/app` 폴더 생성
- [x] 기능 ID prefix별 `src/domains/*` 폴더 생성
- [x] `src/shared` 공통 폴더 생성
- [x] 빈 폴더용 `.gitkeep` 추가
- [x] FE 구조 문서 업데이트
