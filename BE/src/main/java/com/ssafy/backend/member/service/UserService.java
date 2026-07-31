package com.ssafy.backend.member.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.dto.request.UpdateInterestsRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberTypeRequest;
import com.ssafy.backend.member.dto.response.InterestsResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberInterestBrand;
import com.ssafy.backend.member.entity.MemberInterestCategory;
import com.ssafy.backend.member.repository.MemberInterestBrandRepository;
import com.ssafy.backend.member.repository.MemberInterestCategoryRepository;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.dto.response.BrandResponse;
import com.ssafy.backend.product.dto.response.CategoryResponse;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.util.List;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 회원 도메인 서비스 — 온보딩 기본 정보(ONBOARD-001), 관심 브랜드·카테고리(ONBOARD-002),
 * 마이페이지 정보 수정(MY-001) 처리.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {

    private final MemberRepository memberRepository;
    private final MemberInterestBrandRepository memberInterestBrandRepository;
    private final MemberInterestCategoryRepository memberInterestCategoryRepository;
    private final BrandRepository brandRepository;
    private final CategoryRepository categoryRepository;

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

    /**
     * ONBOARD-004: 회원 유형(일반/사업자)을 저장하고 온보딩을 최종 완료 처리한다.
     *
     * <p>이미 온보딩을 완료한 회원이 다시 호출해도 막지 않고 유형을 갱신하며 성공 처리한다(멱등).
     *
     * @param requesterId 요청을 보낸 로그인 회원 ID
     * @param targetId    수정 대상 회원 ID (path variable)
     * @param request     저장할 회원 유형
     * @return 수정 후 회원 프로필
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 정보를 수정하려 할 때 (403)
     */
    @Transactional
    public MemberProfileResponse completeOnboarding(Long requesterId, Long targetId, UpdateMemberTypeRequest request) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        member.completeOnboarding(request.memberType());

        return MemberProfileResponse.from(member);
    }

    /**
     * ONBOARD-002 / MY-001: 관심 브랜드·카테고리 목록을 조회한다.
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 관심 정보를 조회하려 할 때 (403)
     */
    public InterestsResponse getInterests(Long requesterId, Long targetId) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }
        if (!memberRepository.existsById(targetId)) {
            throw new CustomException(ErrorCode.USER_NOT_FOUND);
        }

        List<BrandResponse> brands = memberInterestBrandRepository.findByMember_Id(targetId).stream()
                .map(interest -> BrandResponse.from(interest.getBrand()))
                .toList();
        List<CategoryResponse> categories = memberInterestCategoryRepository.findByMember_Id(targetId).stream()
                .map(interest -> CategoryResponse.from(interest.getCategory()))
                .toList();

        return new InterestsResponse(brands, categories);
    }

    /**
     * ONBOARD-002 / MY-001: 관심 브랜드·카테고리 목록을 전체 교체(replace)한다.
     * 온보딩 최초 완료 시에도, 이후 마이페이지 수정 시에도 같은 엔드포인트를 사용한다.
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 관심 정보를 수정하려 할 때 (403)
     * @throws CustomException BRAND_NOT_FOUND — 존재하지 않는 브랜드 ID가 섞여 있을 때
     * @throws CustomException CATEGORY_NOT_FOUND — 존재하지 않는 카테고리 ID가 섞여 있을 때
     */
    @Transactional
    public InterestsResponse updateInterests(Long requesterId, Long targetId, UpdateInterestsRequest request) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        List<Brand> brands = brandRepository.findAllById(request.brandIds());
        if (brands.size() != Set.copyOf(request.brandIds()).size()) {
            // findAllById는 중복 ID를 한 번만 반환하므로, 단순 size() 비교는 중복 요청 시 오탐한다.
            throw new CustomException(ErrorCode.BRAND_NOT_FOUND);
        }

        List<Category> categories = categoryRepository.findAllById(request.categoryIds());
        if (categories.size() != Set.copyOf(request.categoryIds()).size()) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }

        memberInterestBrandRepository.deleteAllByMemberId(targetId);
        memberInterestCategoryRepository.deleteAllByMemberId(targetId);

        List<MemberInterestBrand> interestBrands = brands.stream()
                .map(brand -> MemberInterestBrand.builder().member(member).brand(brand).build())
                .toList();
        List<MemberInterestCategory> interestCategories = categories.stream()
                .map(category -> MemberInterestCategory.builder().member(member).category(category).build())
                .toList();

        memberInterestBrandRepository.saveAll(interestBrands);
        memberInterestCategoryRepository.saveAll(interestCategories);

        List<BrandResponse> brandResponses = brands.stream().map(BrandResponse::from).toList();
        List<CategoryResponse> categoryResponses = categories.stream().map(CategoryResponse::from).toList();

        return new InterestsResponse(brandResponses, categoryResponses);
    }
}
