package com.ssafy.backend.member.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final String EMAIL = "user@example.com";

    @Mock
    private MemberRepository memberRepository;

    private UserService userService;

    @BeforeEach
    void setUp() {
        userService = new UserService(memberRepository);
    }

    private Member createMember() {
        return Member.builder()
                .email(EMAIL)
                .password("encodedPassword")
                .name("홍길동")
                .build();
    }

    private UpdateMemberRequest createRequest() {
        return new UpdateMemberRequest("빈티지헌터", "01012345678", "서울시 강남구", Gender.MALE);
    }

    @Test
    void 기본_정보를_정상_저장하면_온보딩완료_응답을_반환한다() {
        // given
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberRequest request = createRequest();

        // when
        MemberProfileResponse response = userService.updateBasicInfo(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.nickname()).isEqualTo("빈티지헌터");
        assertThat(response.phoneNumber()).isEqualTo("01012345678");
        assertThat(response.address()).isEqualTo("서울시 강남구");
        assertThat(response.gender()).isEqualTo(Gender.MALE);
        assertThat(response.onboardingCompleted()).isTrue();
    }

    @Test
    void 성별을_보내지_않으면_기존_값을_유지한다() {
        // given
        Member member = createMember();
        member.updateBasicInfo("빈티지헌터", "01012345678", "서울시 강남구", Gender.MALE);
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberRequest request = new UpdateMemberRequest("빈티지헌터2", "01099998888", "부산시 해운대구", null);

        // when
        MemberProfileResponse response = userService.updateBasicInfo(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.nickname()).isEqualTo("빈티지헌터2");
        assertThat(response.gender()).isEqualTo(Gender.MALE);
    }

    @Test
    void 본인이_아닌_타인의_정보를_수정하면_FORBIDDEN_예외가_발생한다() {
        // given
        Long otherMemberId = 999L;

        // when / then
        assertThatThrownBy(() -> userService.updateBasicInfo(MEMBER_ID, otherMemberId, createRequest()))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 존재하지_않는_회원이면_USER_NOT_FOUND_예외가_발생한다() {
        // given
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());

        // when / then
        assertThatThrownBy(() -> userService.updateBasicInfo(MEMBER_ID, MEMBER_ID, createRequest()))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.USER_NOT_FOUND);
    }

    @Test
    void 닉네임_중복이면_NICKNAME_ALREADY_TAKEN_예외가_발생한다() {
        // given
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        doThrow(DataIntegrityViolationException.class).when(memberRepository).flush();

        // when / then
        assertThatThrownBy(() -> userService.updateBasicInfo(MEMBER_ID, MEMBER_ID, createRequest()))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.NICKNAME_ALREADY_TAKEN);
    }
}
