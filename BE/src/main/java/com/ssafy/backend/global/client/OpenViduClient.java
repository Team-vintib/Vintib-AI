package com.ssafy.backend.global.client;

import com.ssafy.backend.global.config.OpenViduConfig.OpenViduProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import io.livekit.server.AccessToken;
import io.livekit.server.CanPublish;
import io.livekit.server.CanPublishData;
import io.livekit.server.CanSubscribe;
import io.livekit.server.RoomJoin;
import io.livekit.server.RoomName;
import io.livekit.server.RoomServiceClient;
import java.io.IOException;
import java.time.Instant;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * OpenVidu v3(LiveKit) 연동 창구. 접속 토큰 발급과 room 정리를 맡는다.
 *
 * <p><b>토큰 발급에는 서버가 필요 없다.</b> LiveKit 접속 토큰은 API key/secret 으로 <b>로컬에서
 * 서명하는 JWT</b> 다 — 미디어 서버에 요청하지 않는다. 그래서 서버 구축(-448)이 끝나기 전에도
 * 발급 로직을 완성하고 검증할 수 있다(계획서 Phase 4의 선행 확인 항목).
 *
 * <p>room 도 미리 만들지 않는다. LiveKit 은 <b>첫 참가자가 들어올 때 room 을 자동 생성</b>하므로
 * 방송 시작 시점에는 이름만 정해 두면 된다. 반대로 <b>삭제는 서버 호출이 필요하다</b>.
 *
 * <p>서버가 죽어 있어도 방송 종료가 막히면 안 되므로 정리 실패는 로그만 남기고 넘어간다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OpenViduClient {

    private final OpenViduProperties properties;

    /**
     * 송출용 토큰(호스트). 발행과 구독을 모두 허용한다.
     *
     * <p>{@code CanPublishData} 도 함께 연다 — 나중에 화면 공유·데이터 채널을 붙일 때 토큰 규약을
     * 다시 바꾸지 않기 위해서다. 실제 사용 여부는 클라이언트가 정한다.
     */
    public String issuePublisherToken(String roomName, String identity, String displayName) {
        return issueToken(roomName, identity, displayName, true);
    }

    /**
     * 시청용 토큰. <b>구독만 허용한다.</b>
     *
     * <p>비회원도 발급받는다 — 라이브 시청이 비회원 공개이기 때문이다. 발행 권한이 없으므로
     * 토큰이 새어 나가도 남의 방송에 영상을 밀어 넣을 수는 없다.
     */
    public String issueViewerToken(String roomName, String identity, String displayName) {
        return issueToken(roomName, identity, displayName, false);
    }

    /** 브라우저가 붙을 주소. 토큰과 함께 내려 FE 가 환경별 주소를 따로 관리하지 않게 한다. */
    public String serverUrl() {
        requireConfigured();
        return properties.serverUrl();
    }

    public Instant expiresAt(Instant issuedAt) {
        return issuedAt.plus(properties.tokenTtl());
    }

    /**
     * 방송이 끝난 room 을 지운다.
     *
     * <p><b>실패해도 예외를 던지지 않는다.</b> 이 호출이 막히면 방송 종료 자체가 실패하는데,
     * 미디어 서버 사정으로 종료가 안 되는 것이 정리가 안 된 것보다 훨씬 나쁘다. 남은 room 은
     * 참가자가 없으면 LiveKit 이 유휴 시간 뒤 스스로 정리한다.
     */
    public void deleteRoom(String roomName) {
        if (!properties.isConfigured() || roomName == null || roomName.isBlank()) {
            return;
        }

        try {
            // 브라우저용 주소가 아니라 내부 API 주소로 붙는다. 운영에서는 도커 네트워크 안이라
            // Caddy·TLS 를 거치지 않는다.
            RoomServiceClient client = RoomServiceClient.createClient(
                    properties.resolvedApiUrl(), properties.apiKey(), properties.apiSecret());
            client.deleteRoom(roomName).execute();
            log.info("OpenVidu room 정리 - room={}", roomName);
        } catch (IOException | RuntimeException e) {
            log.warn("OpenVidu room 정리 실패 - room={} ({})", roomName, e.toString());
        }
    }

    public boolean isConfigured() {
        return properties.isConfigured();
    }

    private String issueToken(String roomName, String identity, String displayName, boolean publisher) {
        requireConfigured();

        AccessToken token = new AccessToken(properties.apiKey(), properties.apiSecret());
        token.setIdentity(identity);
        token.setName(displayName);
        token.setTtl(properties.tokenTtl().toMillis());
        token.addGrants(
                new RoomJoin(true),
                new RoomName(roomName),
                new CanSubscribe(true),
                new CanPublish(publisher),
                new CanPublishData(publisher));

        return token.toJwt();
    }

    private void requireConfigured() {
        if (!properties.isConfigured()) {
            throw new CustomException(ErrorCode.VIDEO_NOT_CONFIGURED);
        }
    }
}
