---
name: scaffold
description: Scaffold a new BE domain package (controller/service/domain/repository/dto) following this project's conventions. Use after a plan in .claude/plans/be/ is approved, when starting to implement a new domain's API endpoints defined in the API spec.
---

# BE 도메인 스캐폴드

승인된 계획(`.claude/plans/be/<번호>-<slug>.md`)의 "구현 목록"을 실제 파일로 만들 때 사용한다. API 명세서(엔드포인트, 요청/응답 필드)는 이미 작성되어 있다는 전제이므로, 그 내용을 아래 템플릿에 맞춰 채워 넣는다 — 필드를 임의로 추정하지 않는다.

## 패키지 규칙

베이스 패키지는 `com.ssafy.backend`. 도메인마다 아래 하위 패키지를 둔다.

```
com.ssafy.backend.<domain>/
├── controller/
├── service/
├── domain/       # JPA 엔티티
├── repository/
└── dto/
```

- `<domain>`은 소문자 영문 도메인명 (예: AUTH→`auth`, PROD→`product`, LIVE→`live`, AUCT→`auction`, POINT→`point`). 계획 파일에 적힌 도메인 코드 기준으로 정하고, 애매하면 사용자에게 확인한다.
- 계획의 "구현 목록"에 있는 항목만 만든다 — 명세서에 없는 엔드포인트나 필드를 미리 만들지 않는다.

## 레이어별 템플릿

### Controller

```java
package com.ssafy.backend.<domain>.controller;

import com.ssafy.backend.<domain>.dto.<Domain>RequestDto;
import com.ssafy.backend.<domain>.dto.<Domain>ResponseDto;
import com.ssafy.backend.<domain>.service.<Domain>Service;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/<resource>")
@RequiredArgsConstructor
public class <Domain>Controller {

    private final <Domain>Service <domain>Service;

    @PostMapping
    public ResponseEntity<<Domain>ResponseDto> create(@Valid @RequestBody <Domain>RequestDto request) {
        return ResponseEntity.ok(<domain>Service.create(request));
    }
}
```

### Service

```java
package com.ssafy.backend.<domain>.service;

import com.ssafy.backend.<domain>.domain.<Entity>;
import com.ssafy.backend.<domain>.dto.<Domain>RequestDto;
import com.ssafy.backend.<domain>.dto.<Domain>ResponseDto;
import com.ssafy.backend.<domain>.repository.<Entity>Repository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class <Domain>Service {

    private final <Entity>Repository <entity>Repository;

    @Transactional
    public <Domain>ResponseDto create(<Domain>RequestDto request) {
        // TODO: 명세서 기준으로 구현
        throw new UnsupportedOperationException();
    }
}
```

클래스 레벨 `@Transactional(readOnly = true)` + 쓰기 메서드에만 `@Transactional`을 얹는 패턴을 기본으로 한다.

### Entity (domain)

```java
package com.ssafy.backend.<domain>.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class <Entity> {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Builder
    private <Entity>(/* 명세서 기준 필드 */) {
        // 필드 대입
    }
}
```

`@Setter`는 붙이지 않는다 (BE/CLAUDE.md 규칙). 상태 변경이 필요하면 의도가 드러나는 메서드를 추가한다.

### Repository

```java
package com.ssafy.backend.<domain>.repository;

import com.ssafy.backend.<domain>.domain.<Entity>;
import org.springframework.data.jpa.repository.JpaRepository;

public interface <Entity>Repository extends JpaRepository<<Entity>, Long> {
}
```

### DTO

요청/응답 DTO는 record + Bean Validation으로 작성한다. 엔드포인트마다 별도 DTO를 만든다 (하나로 돌려쓰지 않는다).

```java
package com.ssafy.backend.<domain>.dto;

import jakarta.validation.constraints.NotBlank;

public record <Domain>RequestDto(
        @NotBlank String example
) {
}
```

```java
package com.ssafy.backend.<domain>.dto;

public record <Domain>ResponseDto(
        Long id
) {
}
```

## 절차

1. 계획 파일의 "구현 목록"을 확인하고, 이번에 만들 엔드포인트/엔티티 범위를 정한다.
2. 위 템플릿 기준으로 필요한 파일만 생성한다. 필드·검증 규칙은 API 명세서를 그대로 옮긴다(추정 금지).
3. 새 도메인 로직에는 최소 하나 이상의 테스트를 함께 작성한다 (`@WebMvcTest` 또는 서비스 단위 테스트 — BE/CLAUDE.md 규칙).
4. 경매(AUCT)처럼 동시성이 걸리는 로직은 Redis 락 등 설계가 아직 미확정이므로, 구현 전 사용자와 방식을 먼저 확인한다.
5. `BE/README.md`의 디렉터리 구조 섹션을 새로 생긴 패키지로 갱신한다.
6. `.claude/skills/verify`로 빌드/테스트를 통과시킨다.