# syntax=docker/dockerfile:1

# ---------- build ----------
FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /workspace

# 의존성 레이어를 소스와 분리해 캐시 적중률을 높인다.
COPY gradlew settings.gradle build.gradle ./
COPY gradle gradle
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon || true

COPY src src
RUN ./gradlew bootJar --no-daemon -x test

# ---------- runtime ----------
FROM eclipse-temurin:21-jre-jammy
# healthcheck용 curl (jre 이미지에 기본 미포함)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /workspace/build/libs/*.jar app.jar

# ⚠️ 타임존을 KST 로 고정한다. 베이스 이미지는 UTC 라 그대로 두면 LocalDateTime.now() 가
#    UTC 벽시계를 준다. 우리 시각 필드는 전부 오프셋 없는 LocalDateTime 이고 DB 컬럼은
#    TIMESTAMPTZ 라, 브라우저가 그 값을 KST 로 읽어 **모든 시각이 9시간 어긋난다.**
#    (방송 시작 시각이 9시간 전으로, 경과 시간이 9시간부터 시작하는 증상)
#    @Future 같은 검증도 같은 축으로 정렬돼야 하므로 JVM 기본 타임존 자체를 바꾼다.
#    compose 의 TZ 환경변수와 중복이지만, 이미지를 단독으로 돌려도 같아야 해서 여기에도 둔다.
ENV TZ=Asia/Seoul

# 로드맵 §2 리소스 예산: Spring 컨테이너 3GB / JVM 힙 2GB
# user.timezone 을 명시하는 이유: TZ 환경변수 해석은 JVM/베이스 이미지에 따라 달라질 여지가
# 있는데, 이 값은 무조건 이긴다. tzdb 는 JRE 가 자체 포함하므로 OS tzdata 유무와 무관하다.
ENV JAVA_OPTS="-Xmx2g -Duser.timezone=Asia/Seoul"
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
