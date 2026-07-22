---
name: verify
description: Run the BE verification harness (Gradle build + tests) that mirrors GitLab CI's be-test job. Use before considering any backend (BE/) code change done, or when the user runs /verify while working in BE/.
---

# BE Verify

`BE/` 코드를 변경했다면 커밋 전에 이 순서로 실행하고, 전부 통과해야 완료로 본다. 루트 `.gitlab-ci.yml`의 `be-test` job과 동일한 검증이다 — 그 job의 스크립트가 바뀌면 이 스킬도 함께 갱신한다.

## 1. 의존 서비스 기동 확인

`@SpringBootTest` 등 Postgres/Redis에 붙는 테스트가 있다. 이미 떠 있지 않다면 루트 디렉터리에서:

```
docker compose up -d postgres redis
```

## 2. 빌드 + 테스트 실행

```
cd BE
./gradlew build --no-daemon --build-cache -Dgradle.user.home=.gradle
```

- 컴파일만 빠르게 반복 확인할 때는 `./gradlew compileJava compileTestJava`
- 테스트만 좁혀서 반복할 때는 `./gradlew test`
- 최종 완료 판단은 반드시 위 `./gradlew build` 전체 통과 기준으로 한다.

## 3. 실패 시

- 컴파일 실패: 에러 메시지의 파일:라인을 확인하고 수정 후 `./gradlew compileJava compileTestJava`로 재확인.
- 테스트 실패: `BE/build/test-results/test/*.xml` 또는 `BE/build/reports/tests/test/index.html`에서 실패 원인 확인 후 수정.
- 통과할 때까지 반복한다.

## 완료 기준

콘솔에 `BUILD SUCCESSFUL`이 출력되면 통과. 그 전까지는 작업을 완료로 보고하지 않는다.