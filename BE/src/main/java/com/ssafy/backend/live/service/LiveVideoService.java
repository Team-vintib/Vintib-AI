package com.ssafy.backend.live.service;

import com.ssafy.backend.global.client.OpenViduClient;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.response.VideoTokenResponse;
import com.ssafy.backend.live.dto.response.VideoTokenResponse.VideoRole;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.Instant;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 영상 접속 토큰 발급(-449).
 *
 * <p><b>역할을 클라이언트가 고르게 하지 않는다.</b> 송출용·시청용 endpoint 를 나누면 FE 가
 * "나는 호스트니까 송출 토큰을 달라"고 요청하는 모양이 되는데, 그 판단은 서버가 해야 한다.
 * endpoint 는 하나이고 호스트 본인일 때만 발행 권한이 붙는다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveVideoService {

    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;
    private final OpenViduClient openViduClient;

    /**
     * 방송 시작 시점에 room 이름을 정한다. <b>미디어 서버를 부르지 않는다</b> — LiveKit 은 첫
     * 참가자가 들어올 때 room 을 자동으로 만든다.
     *
     * <p>이름에 난수를 붙이는 이유는 <b>같은 방송을 다시 열었을 때 이전 room 에 남아 있는 참가자와
     * 섞이지 않게</b> 하기 위해서다. 정리(deleteRoom)가 실패했더라도 새 방송은 새 room 에서 시작한다.
     */
    public static String newRoomName(Long liveId) {
        return "live-" + liveId + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    /**
     * 접속 토큰을 발급한다.
     *
     * @param memberId 로그인 회원 ID. <b>{@code null} 이면 비회원</b>이며 시청 토큰만 받는다
     */
    public VideoTokenResponse issueToken(Long memberId, Long liveId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        // 진행 중인 방송에만 붙을 수 있다. 예정 방송은 room 이 없고, 끝난 방송은 정리됐다.
        if (live.getStatus() != LiveStatus.LIVE || live.getOpenviduRoom() == null) {
            throw new CustomException(ErrorCode.VIDEO_ROOM_NOT_READY);
        }

        String roomName = live.getOpenviduRoom();
        boolean host = live.isHostedBy(memberId);
        Instant now = Instant.now();

        // identity 는 LiveKit 안에서 참가자를 구분하는 키다. 같은 값으로 두 번 접속하면
        // 먼저 붙어 있던 쪽이 끊긴다.
        //
        // 호스트는 그 성질을 그대로 쓴다 — 네트워크가 끊겼다 재접속하면 유령 송출이 남는 대신
        // 교체된다. 시청자는 반대로 난수를 붙인다. 같은 사람이 두 기기로 보는 것이 정상이라
        // 서로 끊어버리면 안 된다.
        String identity = host
                ? "host-" + memberId
                : viewerIdentity(memberId);

        String token = host
                ? openViduClient.issuePublisherToken(roomName, identity, displayName(memberId))
                : openViduClient.issueViewerToken(roomName, identity, displayName(memberId));

        return VideoTokenResponse.of(
                roomName,
                token,
                openViduClient.serverUrl(),
                host ? VideoRole.PUBLISHER : VideoRole.VIEWER,
                openViduClient.expiresAt(now));
    }

    private String viewerIdentity(Long memberId) {
        String suffix = UUID.randomUUID().toString().substring(0, 8);
        return memberId == null ? "guest-" + suffix : "viewer-" + memberId + "-" + suffix;
    }

    /**
     * 화면에 뜨는 이름. 비회원은 식별할 값이 없어 고정 문구를 쓴다.
     *
     * <p>회원이면 온보딩을 완료해야 이 기능(영상 접속) 자체를 쓸 수 있고(SY019 게이트), 온보딩
     * 완료는 닉네임이 있어야만 가능하므로(SY019 순서 보장) 여기 도달한 회원은 항상 닉네임이 있다.
     */
    private String displayName(Long memberId) {
        if (memberId == null) {
            return "게스트";
        }
        return memberRepository.findById(memberId)
                .map(Member::getNickname)
                .orElse("게스트");
    }
}
