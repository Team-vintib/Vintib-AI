package com.ssafy.backend.member.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 회원 도메인 서비스 — 온보딩 기본 정보(ONBOARD-001) 및 마이페이지 정보 수정(MY-001) 처리.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {

    private final MemberRepository memberRepository;

    /**
     * ONBOARD-001 / MY-001: 닉네임·전화번호·주소·상세주소·우편번호·성별을 저장하고 회원 프로필을 반환한다.
     *
     * <p>온보딩 최초 완료 시에도, 이후 마이페이지 수정 시에도 같은 엔드포인트를 사용한다.
     * 닉네임 중복은 DB unique 제약으로 최종 방어하고 DataIntegrityViolationException 을
     * NICKNAME_ALREADY_TAKEN 으로 변환한다.
     *
     * @param requesterId 요청을 보낸 로그인 회원 ID (컨트롤러에서 JWT 기반으로 추출)
     * @param targetId    수정 대상 회원 ID (path variable)
     * @param request     변경할 정보
     * @return 수정 후 회원 프로필
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 정보를 수정하려 할 때 (403)
     * @throws CustomException NICKNAME_ALREADY_TAKEN — 닉네임 중복
     */
    @Transactional
    public MemberProfileResponse updateBasicInfo(Long requesterId, Long targetId, UpdateMemberRequest request) {
        if (!requesterId.equals(targetId)) {
            // IDOR 방지: 존재 여부도 드러내지 않고 403 반환
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        member.updateBasicInfo(
                request.nickname(),
                request.phoneNumber(),
                request.address(),
                request.detailAddress(),
                request.postalCode(),
                request.gender()
        );

        try {
            memberRepository.flush();
        } catch (DataIntegrityViolationException e) {
            // unique 제약(닉네임 중복) 위반을 도메인 예외로 변환
            throw new CustomException(ErrorCode.NICKNAME_ALREADY_TAKEN);
        }

        return MemberProfileResponse.from(member);
    }
}
