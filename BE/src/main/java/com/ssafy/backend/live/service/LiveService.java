package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.request.LiveScheduleRequest;
import com.ssafy.backend.live.dto.response.LiveResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
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
        Member host = memberRepository.findById(hostId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        Live live = Live.schedule(host, request.title(), request.thumbnailUrl(), request.scheduledAt());

        return LiveResponse.from(liveRepository.save(live));
    }
}