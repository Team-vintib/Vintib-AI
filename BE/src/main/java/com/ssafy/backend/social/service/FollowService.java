package com.ssafy.backend.social.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.social.dto.response.FollowResponse;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class FollowService {

    private final FollowRepository followRepository;
    private final MemberRepository memberRepository;

    @Transactional
    public FollowResponse follow(Long followerId, Long targetId) {
        if (followerId.equals(targetId)) {
            throw new CustomException(ErrorCode.SELF_FOLLOW_NOT_ALLOWED);
        }

        // 이미 팔로우 중이어도 에러 없이 현재 상태를 그대로 반환한다(멱등) — 팔로우 버튼을
        // 스위치처럼 연타해도 항상 안전하게 동작해야 한다는 요구에 따른 정책이다.
        if (!followRepository.existsByFollower_IdAndFollowing_Id(followerId, targetId)) {
            Member follower = memberRepository.findById(followerId)
                    .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
            Member target = memberRepository.findById(targetId)
                    .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
            followRepository.save(Follow.builder().follower(follower).following(target).build());
        }

        return new FollowResponse(targetId, true, followRepository.countByFollowing_Id(targetId));
    }

    @Transactional
    public void unfollow(Long followerId, Long targetId) {
        // 팔로우 중이 아니었어도 결과 상태(비팔로우)는 같으므로 에러 없이 멱등하게 처리한다.
        followRepository.deleteByFollower_IdAndFollowing_Id(followerId, targetId);
    }
}
