# ONBOARD-001 공통 레이아웃 및 단계 표시 구현 계획

## 배경/목표

ONBOARD-001~004에서 함께 사용할 온보딩 레이아웃과 4단계 진행 표시를 구현한다.
확정된 Notion 문서와 Figma VinTib 화면의 디자인 언어를 기준으로 한다.

## 작업 내용

- Ivory 배경과 Forest Green 강조색을 디자인 토큰으로 정의한다.
- 현재·완료·미완료 상태를 구분하는 4단계 진행 표시를 구현한다.
- 제목, 안내, 콘텐츠, 이전·다음 버튼을 배치하는 공통 온보딩 레이아웃을 구현한다.
- 공통 버튼에 Hover, Focus, Disabled 상태를 구현한다.
- ONBOARD-001을 확인할 수 있는 기본 화면과 라우트를 추가한다.
- 단계 표시에 의미 있는 목록 구조와 `aria-current`를 사용한다.

## 구현 목록

- [x] 전역 디자인 토큰 추가
- [x] BaseButton 공통 컴포넌트 추가
- [x] OnboardingStepIndicator 컴포넌트 추가
- [x] OnboardingLayout 공통 레이아웃 추가
- [x] OnboardingBasicInfoView 기본 화면 추가
- [x] ONBOARD-001 확인용 라우트 추가
- [x] 키보드 Focus와 접근성 상태 확인
- [x] lint, type-check, build 및 브라우저 확인
