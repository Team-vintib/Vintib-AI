package com.ssafy.backend.member.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.dto.request.UpdateInterestsRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberTypeRequest;
import com.ssafy.backend.member.dto.response.InterestsResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Gender;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberInterestBrand;
import com.ssafy.backend.member.entity.MemberInterestCategory;
import com.ssafy.backend.member.entity.MemberType;
import com.ssafy.backend.member.repository.MemberInterestBrandRepository;
import com.ssafy.backend.member.repository.MemberInterestCategoryRepository;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.List;
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

    @Mock
    private MemberInterestBrandRepository memberInterestBrandRepository;

    @Mock
    private MemberInterestCategoryRepository memberInterestCategoryRepository;

    @Mock
    private BrandRepository brandRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private Brand nike;

    @Mock
    private Category outer;

    private UserService userService;

    @BeforeEach
    void setUp() {
        userService = new UserService(
                memberRepository,
                memberInterestBrandRepository,
                memberInterestCategoryRepository,
                brandRepository,
                categoryRepository);
    }

    private Member createMember() {
        return Member.builder()
                .email(EMAIL)
                .password("encodedPassword")
                .name("홍길동")
                .build();
    }

    private UpdateMemberRequest createRequest() {
        return new UpdateMemberRequest(
                "빈티지헌터", "01012345678", "서울시 강남구", "3층", "06236", Gender.MALE);
    }

    @Test
    void 기본_정보를_정상_저장한다() {
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
        assertThat(response.detailAddress()).isEqualTo("3층");
        assertThat(response.postalCode()).isEqualTo("06236");
        assertThat(response.gender()).isEqualTo(Gender.MALE);
        // 온보딩 최종 완료는 ONBOARD-004(회원 유형 저장) 시점으로 옮겨졌다 (SY021).
        assertThat(response.onboardingCompleted()).isFalse();
    }

    @Test
    void 우편번호는_없어도_저장된다() {
        // given: 주소 검색을 안 쓰고 직접 입력하면 우편번호가 없을 수 있다.
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberRequest request =
                new UpdateMemberRequest("빈티지헌터", "01012345678", "서울시 강남구", "3층", null, Gender.MALE);

        // when
        MemberProfileResponse response = userService.updateBasicInfo(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.postalCode()).isNull();
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

    @Test
    void 회원_유형을_저장하면_온보딩완료_응답을_반환한다() {
        // given
        Member member = createMember();
        member.updateBasicInfo("빈티지헌터", "01012345678", "서울시 강남구", "3층", "06236", Gender.MALE);
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberTypeRequest request = new UpdateMemberTypeRequest(MemberType.BUSINESS);

        // when
        MemberProfileResponse response = userService.completeOnboarding(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.memberType()).isEqualTo(MemberType.BUSINESS);
        assertThat(response.onboardingCompleted()).isTrue();
    }

    @Test
    void 본인이_아닌_회원의_유형을_저장하면_FORBIDDEN_예외가_발생한다() {
        // given
        Long otherMemberId = 999L;
        UpdateMemberTypeRequest request = new UpdateMemberTypeRequest(MemberType.GENERAL);

        // when / then
        assertThatThrownBy(() -> userService.completeOnboarding(MEMBER_ID, otherMemberId, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 존재하지_않는_회원이면_유형_저장시_USER_NOT_FOUND_예외가_발생한다() {
        // given
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        UpdateMemberTypeRequest request = new UpdateMemberTypeRequest(MemberType.GENERAL);

        // when / then
        assertThatThrownBy(() -> userService.completeOnboarding(MEMBER_ID, MEMBER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.USER_NOT_FOUND);
    }

    @Test
    void 이미_온보딩을_완료한_회원이_다시_요청해도_정상_처리된다() {
        // given: 재요청은 멱등 성공으로 처리한다 — 유형만 갱신하고 막지 않는다.
        Member member = createMember();
        member.updateBasicInfo("빈티지헌터", "01012345678", "서울시 강남구", "3층", "06236", Gender.MALE);
        member.completeOnboarding(MemberType.GENERAL);
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberTypeRequest request = new UpdateMemberTypeRequest(MemberType.BUSINESS);

        // when
        MemberProfileResponse response = userService.completeOnboarding(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.memberType()).isEqualTo(MemberType.BUSINESS);
        assertThat(response.onboardingCompleted()).isTrue();
    }

    @Test
    void 닉네임이_없으면_회원_유형_저장시_ONBOARDING_BASIC_INFO_REQUIRED_예외가_발생한다() {
        // given: ONBOARD-001(기본 정보 저장)을 건너뛰고 004(회원 유형)부터 부른 경우.
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateMemberTypeRequest request = new UpdateMemberTypeRequest(MemberType.GENERAL);

        // when / then
        assertThatThrownBy(() -> userService.completeOnboarding(MEMBER_ID, MEMBER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ONBOARDING_BASIC_INFO_REQUIRED);
    }

    @Test
    void 관심_브랜드_카테고리를_정상_조회한다() {
        // given
        when(memberRepository.existsById(MEMBER_ID)).thenReturn(true);
        when(nike.getId()).thenReturn(1L);
        when(nike.getName()).thenReturn("나이키");
        when(nike.getNameEn()).thenReturn("Nike");
        when(outer.getId()).thenReturn(1L);
        when(outer.getParentId()).thenReturn(null);
        when(outer.getName()).thenReturn("아우터");
        when(outer.getDepth()).thenReturn((short) 1);

        MemberInterestBrand interestBrand =
                MemberInterestBrand.builder().member(createMember()).brand(nike).build();
        MemberInterestCategory interestCategory =
                MemberInterestCategory.builder().member(createMember()).category(outer).build();
        when(memberInterestBrandRepository.findByMember_Id(MEMBER_ID)).thenReturn(List.of(interestBrand));
        when(memberInterestCategoryRepository.findByMember_Id(MEMBER_ID)).thenReturn(List.of(interestCategory));

        // when
        InterestsResponse response = userService.getInterests(MEMBER_ID, MEMBER_ID);

        // then
        assertThat(response.brands()).hasSize(1);
        assertThat(response.brands().get(0).name()).isEqualTo("나이키");
        assertThat(response.categories()).hasSize(1);
        assertThat(response.categories().get(0).name()).isEqualTo("아우터");
    }

    @Test
    void 본인이_아닌_타인의_관심_정보를_조회하면_FORBIDDEN_예외가_발생한다() {
        Long otherMemberId = 999L;

        assertThatThrownBy(() -> userService.getInterests(MEMBER_ID, otherMemberId))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.MEMBER_FORBIDDEN);
    }

    @Test
    void 관심_정보_수정시_존재하지_않는_브랜드가_섞여있으면_BRAND_NOT_FOUND_예외가_발생한다() {
        // given
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(brandRepository.findAllById(List.of(1L, 2L))).thenReturn(List.of(nike));

        UpdateInterestsRequest request = new UpdateInterestsRequest(List.of(1L, 2L), List.of());

        // when / then
        assertThatThrownBy(() -> userService.updateInterests(MEMBER_ID, MEMBER_ID, request))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.BRAND_NOT_FOUND);
    }

    @Test
    void 같은_브랜드_ID를_중복으로_요청해도_정상_처리된다() {
        // given: findAllById는 중복 ID를 한 번만 반환하므로, 단순 size() 비교로는 오탐할 수 있다.
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(nike.getId()).thenReturn(1L);
        when(nike.getName()).thenReturn("나이키");
        when(nike.getNameEn()).thenReturn("Nike");
        when(brandRepository.findAllById(List.of(1L, 1L))).thenReturn(List.of(nike));

        UpdateInterestsRequest request = new UpdateInterestsRequest(List.of(1L, 1L), List.of());

        // when
        InterestsResponse response = userService.updateInterests(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.brands()).hasSize(1);
        assertThat(response.brands().get(0).name()).isEqualTo("나이키");
    }

    @Test
    void 빈_배열로_수정하면_기존_관심_정보가_전부_삭제된다() {
        // given: 관심 브랜드/카테고리는 선택 입력이라 건너뛸 수 있다.
        Member member = createMember();
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));

        UpdateInterestsRequest request = new UpdateInterestsRequest(List.of(), List.of());

        // when
        InterestsResponse response = userService.updateInterests(MEMBER_ID, MEMBER_ID, request);

        // then
        assertThat(response.brands()).isEmpty();
        assertThat(response.categories()).isEmpty();
        verify(memberInterestBrandRepository).deleteAllByMemberId(MEMBER_ID);
        verify(memberInterestCategoryRepository).deleteAllByMemberId(MEMBER_ID);
    }
}
