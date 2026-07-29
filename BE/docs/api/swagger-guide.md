# FE 개발자를 위한 Swagger 사용 가이드

백엔드 API를 어떻게 확인하고 호출하는지 정리한 문서입니다. Swagger를 처음 쓰는 분 기준으로 썼습니다.

## 1. Swagger가 뭔가요

백엔드가 만든 **API 목록·요청 형식·응답 형식을 자동으로 보여주는 웹 페이지**입니다.

백엔드 코드에서 자동 생성되기 때문에, 백엔드가 API를 추가하면 **문서도 자동으로 갱신**됩니다. 따로 문서를 받아볼 필요 없이 이 페이지만 보면 됩니다. 브라우저에서 **직접 호출해보는 것도 가능**합니다.

## 2. 어디로 접속하나요

| 환경 | 주소 |
| --- | --- |
| 배포 서버 | `https://i15a108.p.ssafy.io/swagger-ui.html` |
| 로컬(백엔드를 직접 띄운 경우) | `http://localhost:8080/swagger-ui.html` |

배포 서버는 `develop-BE`에 병합될 때마다 자동 배포되므로, 병합된 API는 곧 위 주소에 반영됩니다.

## 3. 지금 볼 수 있는 API

| 태그 | 엔드포인트 | 설명 | 인증 |
| --- | --- | --- | --- |
| 시스템 | `GET /api/health` | 서버가 살아있는지 확인 | 불필요 |
| 인증/회원 | `POST /api/auth/email/check-duplicate` | 이메일 중복 확인 | 불필요 |
| 인증/회원 | `POST /api/auth/email/send-code` | 인증 코드 발송 | 불필요 |
| 인증/회원 | `POST /api/auth/email/verify-code` | 인증 코드 확인 | 불필요 |
| 인증/회원 | `POST /api/auth/signup` | 회원가입 | 불필요 |
| 인증/회원 | `POST /api/auth/signin` | 로그인 (토큰 발급) | 불필요 |
| 인증/회원 | `POST /api/auth/reissue` | 액세스 토큰 재발급 | 불필요 |
| 인증/회원 | `POST /api/auth/logout` | 로그아웃 | **필요** |
| 홈 | `GET /api/home` | 홈 콘텐츠 조회 (현재 Mock) | 불필요 |
| 홈 | `GET /api/home/following` | 팔로잉 콘텐츠 조회 (현재 Mock) | **필요** |
| 상품 | `POST /api/products` | 상품 기본 정보 등록 | **필요** |
| 상품 | `PATCH /api/products/{id}/status` | 판매 가격 설정·상시 판매 등록 | **필요** |

> 홈 API 두 개는 아직 **Mock 데이터**를 반환합니다. 응답 형태는 확정된 것이라 화면 개발을 시작하셔도 되지만, 값은 실제 데이터가 아닙니다.

라이브·경매·채팅 API는 개발 중입니다. 개발되는 대로 이 페이지에 **자동으로 추가**되니, 주기적으로 열어보시면 됩니다.

## 4. 화면 보는 법

Swagger 페이지는 이렇게 구성됩니다.

```
시스템                          ← 태그(도메인별 그룹)
  GET  /api/health   헬스체크   ← 엔드포인트: 메서드 + 경로 + 설명
홈
  GET  /api/home     홈 콘텐츠 조회
```

엔드포인트를 클릭하면 펼쳐집니다.

| 항목 | 의미 |
| --- | --- |
| **Parameters** | URL에 붙는 값 (경로 변수 `/products/{id}`, 쿼리 `?page=0`) |
| **Request body** | POST/PUT에서 보낼 JSON 형태 |
| **Responses** | 상태 코드별 응답 형태 (200 성공, 400 잘못된 요청 등) |
| **Schemas** (맨 아래) | 요청·응답에 쓰이는 데이터 구조 정의 |

`Example Value`를 누르면 실제 JSON 예시가, `Schema`를 누르면 각 필드의 타입·설명이 보입니다.

## 5. 직접 호출해보기 (Try it out)

1. 엔드포인트를 펼칩니다
2. 오른쪽 **`Try it out`** 버튼 클릭
3. 필요한 값을 입력합니다 (없으면 생략)
4. **`Execute`** 클릭
5. 아래 **Server response**에 실제 응답이 나옵니다

`curl` 명령어도 같이 보여주니, 그대로 복사해 터미널에서 써도 됩니다.

## 6. ⭐ 공통 응답 규격 — 가장 중요합니다

**모든 API 응답은 아래 껍데기로 한 번 감싸져 있습니다.** FE에서는 항상 이걸 벗겨서 써야 합니다.

**성공했을 때**

```json
{
  "success": true,
  "data": { "backend": "UP", "aiServer": "UP" },
  "error": null
}
```

**실패했을 때**

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "A002",
    "message": "입찰 금액이 현재 최고가보다 낮습니다.",
    "errors": null
  }
}
```

즉 실제 필요한 값은 항상 **`data` 안에** 있습니다. `success`로 성공·실패를 판단하면 됩니다.

**입력값 검증에 실패하면** `error.errors`에 어떤 필드가 왜 틀렸는지 배열로 들어옵니다.

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "C001",
    "message": "잘못된 입력값입니다.",
    "errors": [
      { "field": "amount", "value": "-100", "reason": "양수여야 합니다" }
    ]
  }
}
```

폼 화면에서 필드별 에러 메시지를 띄울 때 이 배열을 그대로 쓰시면 됩니다.

## 7. 에러 코드 체계

`error.code`는 **알파벳 접두어 + 숫자**입니다. 접두어로 어느 도메인 문제인지 알 수 있습니다.

| 접두어 | 도메인 | 예시 |
| --- | --- | --- |
| `C` | 공통 | `C001` 잘못된 입력값 / `C002` 서버 내부 오류 |
| `U` | 인증·회원 | `U001` 존재하지 않는 사용자 |
| `L` | 라이브·채팅 | `L001` 라이브 없음 |
| `A` | 경매·입찰 | `A002` 입찰 금액이 현재 최고가보다 낮음 |
| `W` | 포인트·출금 | `W001` 포인트 잔액 부족 |
| `O` | 주문 | `O001` 현재 상태에서 처리 불가 |
| `T` | AI 가상 시착 | `T001` 시착 프로필 미등록 |
| `P` | 상품 | `P001` 존재하지 않는 상품 / `P002` 본인 상품이 아님 |

`error.message`는 사용자에게 그대로 보여줘도 되는 한국어 문구입니다. 화면 문구를 따로 만들지 않아도 됩니다.

## 8. FE 코드에서 호출하는 예시

응답 껍데기를 벗기는 공통 함수를 하나 만들어두면 편합니다.

```js
const BASE_URL = import.meta.env.VITE_API_BASE_URL; // 예: https://i15a108.p.ssafy.io

async function api(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  const body = await res.json();

  if (!body.success) {
    // error.code 로 분기하거나, error.message 를 그대로 표시
    throw new Error(`[${body.error.code}] ${body.error.message}`);
  }

  return body.data; // 껍데기를 벗겨 실제 데이터만 반환
}
```

사용하는 쪽:

```js
const health = await api('/api/health');
console.log(health.backend); // "UP"
```

## 9. 인증(로그인)은 어떻게 되나요

**JWT 인증이 붙어 있습니다.** 위 표에서 "인증 **필요**"인 API는 토큰 없이 호출하면 `401`이 납니다.

가입·인증 과정에서 토큰처럼 생긴 값이 두 번 나오는데, **용도가 서로 다릅니다.** 헷갈리기 쉬운 부분이라 정리합니다.

| 값 | 어디서 나오나 | 용도 |
| --- | --- | --- |
| `verificationToken` | `POST /api/auth/email/verify-code` (인증코드 확인) | **회원가입 전용, 1회성.** `POST /api/auth/signup` 요청에 실어 보내는 용도일 뿐, API 인증에는 못 씁니다. |
| `accessToken` / `refreshToken` | `POST /api/auth/signin` (로그인) | **실제 API 인증용.** 이 값을 `Authorization` 헤더에 넣어야 인증 필요한 API를 호출할 수 있습니다. |

즉 회원가입(`signup`)이 끝났다고 바로 토큰이 생기는 게 아니라, **가입 후 로그인(`signin`)을 한 번 더 호출해야** `accessToken`을 받습니다.

1. `POST /api/auth/signin`으로 로그인하면 `accessToken`/`refreshToken`이 나옵니다.
2. 이후 요청 헤더에 `Authorization: Bearer <accessToken>`을 붙입니다.
3. `accessToken`이 만료되면(15분) `POST /api/auth/reissue`로 재발급받습니다.

**Swagger 화면에 `Authorize` 버튼이 생겼습니다.** 우측 상단 자물쇠 아이콘을 클릭 → `signin` 응답의 `accessToken` 값을 **`Bearer ` 접두어 없이** 그대로 붙여넣고 Authorize → Close 하면, 이후 `Try it out`으로 호출하는 모든 요청에 `Authorization` 헤더가 자동으로 실립니다. 더 이상 `curl`/Postman에서 헤더를 직접 붙일 필요 없습니다.

명시된 것 외의 모든 경로는 기본적으로 **인증이 필요합니다.** 새 API가 추가되면 공개 여부를 따로 안내드립니다.

## 10. ⚠️ 미리 알아두실 제약

**CORS가 아직 설정되지 않았습니다.**

FE 화면(`localhost:5173`, Vercel 등)에서 백엔드로 직접 요청하면 **브라우저가 차단**합니다. Swagger 페이지 안에서의 `Try it out`은 같은 출처라 정상 동작하지만, FE 코드에서 호출하면 아래 에러가 납니다.

```
Access to fetch at 'https://i15a108.p.ssafy.io/...' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**FE 개발을 시작하기 전에 백엔드에 CORS 허용을 요청해 주세요.** 이때 **FE 주소(로컬 포트, 배포된 Vercel 도메인)를 알려주셔야** 허용 목록에 넣을 수 있습니다.

**개발 중 데이터는 초기화됩니다.** MVP 단계라 백엔드가 재배포될 때마다 DB가 비워집니다. 테스트 데이터가 사라져도 정상입니다.

## 11. 문의

- API 스펙이 궁금하거나 응답 형태를 바꿔야 하면 백엔드(정윤·서윤)에게 말씀해 주세요.
- Swagger에 안 보이는 API는 아직 개발 전입니다.
