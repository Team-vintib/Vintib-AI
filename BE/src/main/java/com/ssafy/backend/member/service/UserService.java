package com.ssafy.backend.member.service;

import com.ssafy.backend.business.entity.BusinessVerificationStatus;
import com.ssafy.backend.business.repository.BusinessInfoRepository;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.live.service.LiveService;
import com.ssafy.backend.member.dto.request.UpdateBioRequest;
import com.ssafy.backend.member.dto.request.UpdateInterestsRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberRequest;
import com.ssafy.backend.member.dto.request.UpdateMemberTypeRequest;
import com.ssafy.backend.member.dto.response.InterestsResponse;
import com.ssafy.backend.member.dto.response.MemberProfileResponse;
import com.ssafy.backend.member.dto.response.MypageSummaryResponse;
import com.ssafy.backend.member.dto.response.PublicProfileResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.entity.MemberInterestBrand;
import com.ssafy.backend.member.entity.MemberInterestCategory;
import com.ssafy.backend.member.repository.MemberInterestBrandRepository;
import com.ssafy.backend.member.repository.MemberInterestCategoryRepository;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.notification.repository.NotificationRepository;
import com.ssafy.backend.order.repository.OrderRepository;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.product.dto.response.BrandResponse;
import com.ssafy.backend.product.dto.response.CategoryResponse;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.repository.FollowRepository;
import com.ssafy.backend.social.repository.WishRepository;
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
    private final BusinessInfoRepository businessInfoRepository;
    private final OrderRepository orderRepository;
    private final WishRepository wishRepository;
    private final FollowRepository followRepository;
    private final NotificationRepository notificationRepository;
    private final PointAccountRepository pointAccountRepository;
    private final LiveRepository liveRepository;
    private final ProductRepository productRepository;

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

        return MemberProfileResponse.from(member, businessVerificationStatusOf(targetId));
    }

    /**
     * 소개글을 저장한다(011 §5). {@link #updateBasicInfo}와 마찬가지로 매번 전체를 새로 받는다
     * (부분 수정 아님) — 값을 안 보내면 지워진다. 커버 이미지는 {@link MemberImageService}가
     * 별도로 관리한다(SY030).
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 정보를 수정하려 할 때 (403)
     */
    @Transactional
    public MemberProfileResponse updateBio(Long requesterId, Long targetId, UpdateBioRequest request) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        member.updateBio(request.description());

        return MemberProfileResponse.from(member, businessVerificationStatusOf(targetId));
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
     * @throws CustomException ONBOARDING_BASIC_INFO_REQUIRED — ONBOARD-001을 아직 안 거쳐 닉네임이 없을 때
     */
    @Transactional
    public MemberProfileResponse completeOnboarding(Long requesterId, Long targetId, UpdateMemberTypeRequest request) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        // 온보딩 순서 보장(SY019) — ONBOARD-001을 건너뛰고 004부터 부르면 닉네임이 null인 채로
        // onboardingCompleted만 true가 될 수 있어, "완료된 회원은 항상 닉네임이 있다"는 게이트 전제가 깨진다.
        if (member.getNickname() == null) {
            throw new CustomException(ErrorCode.ONBOARDING_BASIC_INFO_REQUIRED);
        }

        member.completeOnboarding(request.memberType());

        return MemberProfileResponse.from(member, businessVerificationStatusOf(targetId));
    }

    /**
     * MY-001: 회원 본인의 기본 정보를 조회한다.
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 정보를 조회하려 할 때 (403)
     */
    public MemberProfileResponse getProfile(Long requesterId, Long targetId) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        return MemberProfileResponse.from(member, businessVerificationStatusOf(targetId));
    }

    /**
     * 에픽 S15P11A108-207 보너스: 마이페이지 첫 화면 카운터(구매/판매/찜/팔로워/안읽은 알림)와
     * 포인트 잔액을 한 번에 조회한다. 포인트 계좌가 아직 없는 회원은 0으로 본다(계좌 생성은
     * {@code PointService} 조회/충전/출금 경로에서만 일어난다 — 이 요약 조회가 부수효과로
     * 계좌를 만들지는 않는다).
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     * @throws CustomException MEMBER_FORBIDDEN — 본인 외 타인의 요약을 조회하려 할 때 (403)
     */
    public MypageSummaryResponse getMypageSummary(Long requesterId, Long targetId) {
        if (!requesterId.equals(targetId)) {
            throw new CustomException(ErrorCode.MEMBER_FORBIDDEN);
        }

        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        long pointBalance = pointAccountRepository.findById(targetId)
                .map(PointAccount::getAvailable)
                .orElse(0L);

        return MypageSummaryResponse.of(
                member,
                businessVerificationStatusOf(targetId),
                orderRepository.countByBuyer_Id(targetId),
                orderRepository.countBySeller_Id(targetId),
                wishRepository.countByMember_Id(targetId),
                followRepository.countByFollowing_Id(targetId),
                notificationRepository.countByMember_IdAndReadFalse(targetId),
                pointBalance);
    }

    /**
     * 공개 회원/판매자 프로필 조회(011 §3.3). 비회원도 조회 가능해 {@code viewerId}가 {@code null}일
     * 수 있다 — 그때 {@code isFollowing}은 항상 {@code false}다(팔로워/팔로잉 목록 조회와 동일 정책).
     *
     * @throws CustomException USER_NOT_FOUND — 대상 회원이 없을 때
     */
    public PublicProfileResponse getPublicProfile(Long viewerId, Long targetId) {
        Member member = memberRepository.findById(targetId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        boolean isFollowing = viewerId != null
                && followRepository.existsByFollower_IdAndFollowing_Id(viewerId, targetId);
        boolean businessVerified = businessInfoRepository.findById(targetId)
                .map(businessInfo -> businessInfo.getVerificationStatus() == BusinessVerificationStatus.APPROVED)
                .orElse(false);

        return PublicProfileResponse.of(
                member,
                followRepository.countByFollowing_Id(targetId),
                followRepository.countByFollower_Id(targetId),
                productRepository.countBySeller_IdAndSaleStatusNot(targetId, SaleStatus.DRAFT),
                liveRepository.countByHost_IdAndStatusIn(targetId, LiveService.PUBLIC_STATUSES),
                isFollowing,
                businessVerified);
    }

    private String businessVerificationStatusOf(Long memberId) {
        return businessInfoRepository.findById(memberId)
                .map(businessInfo -> businessInfo.getVerificationStatus().name())
                .orElse("NONE");
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
