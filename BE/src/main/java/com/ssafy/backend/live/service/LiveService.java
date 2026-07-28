package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.request.LiveInstantRequest;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.time.LocalDateTime;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveService {

    private final LiveRepository liveRepository;
    private final MemberRepository memberRepository;

    /**
     * 예약 라이브 개설(LIVE-001). 방송 예정 시각이 미래인지는 요청 DTO({@code @Future})가 검증한다.
     */
    @Transactional
    public LiveResponse scheduleLive(Long hostId, LiveScheduleRequest request) {
        Member host = findHost(hostId);

        Live live = Live.schedule(host, request.title(), request.thumbnailUrl(), request.scheduledAt());

        return LiveResponse.from(liveRepository.save(live));
    }

    /**
     * 즉시 라이브 개설(LIVE-002). 예약을 거치지 않고 곧바로 LIVE 상태로 만든다.
     *
     * <p>시작 시각은 클라이언트가 보낸 값이 아니라 서버 시각으로 박는다 — 방송 시작 순서·경매 종료
     * 판정이 전부 서버 시각 기준이어야 하기 때문이다(erd.md §6).
     */
    @Transactional
    public LiveResponse openLiveNow(Long hostId, LiveInstantRequest request) {
        Member host = findHost(hostId);

        Live live = Live.openNow(host, request.title(), request.thumbnailUrl(), LocalDateTime.now());

        return LiveResponse.from(liveRepository.save(live));
    }

    private Member findHost(Long hostId) {
        return memberRepository.findById(hostId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}