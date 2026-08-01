package com.ssafy.backend.social.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.dto.response.FollowResponse;
import com.ssafy.backend.social.dto.response.FollowUserResponse;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class FollowService {

    private final FollowRepository followRepository;
    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;

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

    public PageResponse<FollowUserResponse> getFollowers(Long userId, Long viewerId, Pageable pageable) {
        requireMemberExists(userId);
        Page<Follow> page = followRepository.findByFollowing_Id(userId, sortedByLatest(pageable));
        return toResponse(page.map(Follow::getFollower), viewerId);
    }

    public PageResponse<FollowUserResponse> getFollowings(Long userId, Long viewerId, Pageable pageable) {
        requireMemberExists(userId);
        Page<Follow> page = followRepository.findByFollower_Id(userId, sortedByLatest(pageable));
        return toResponse(page.map(Follow::getFollowing), viewerId);
    }

    private void requireMemberExists(Long userId) {
        if (!memberRepository.existsById(userId)) {
            throw new CustomException(ErrorCode.USER_NOT_FOUND);
        }
    }

    // 최신 팔로우순 고정 — 클라이언트가 다른 sort를 보내도 무시한다(WishService.getWishList와 동일한 정책).
    private Pageable sortedByLatest(Pageable pageable) {
        return PageRequest.of(
                pageable.getPageNumber(), pageable.getPageSize(), Sort.by(Sort.Direction.DESC, "createdAt"));
    }

    private PageResponse<FollowUserResponse> toResponse(Page<Member> members, Long viewerId) {
        List<Long> memberIds = members.getContent().stream().map(Member::getId).toList();

        Map<Long, Long> followerCounts = memberIds.isEmpty()
                ? Map.of()
                : followRepository.countFollowersByMemberIds(memberIds).stream()
                        .collect(Collectors.toMap(
                                FollowRepository.MemberFollowerCount::getMemberId,
                                FollowRepository.MemberFollowerCount::getCount));
        Map<Long, Long> productCounts = memberIds.isEmpty()
                ? Map.of()
                : productRepository.countBySellerIdsAndSaleStatusNot(memberIds, SaleStatus.DRAFT).stream()
                        .collect(Collectors.toMap(
                                ProductRepository.SellerProductCount::getSellerId,
                                ProductRepository.SellerProductCount::getCount));
        Set<Long> followingByViewer = (viewerId == null || memberIds.isEmpty())
                ? Set.of()
                : followRepository.findFollowingIdsAmong(viewerId, memberIds);

        return PageResponse.from(members.map(member -> FollowUserResponse.of(
                member,
                followerCounts.getOrDefault(member.getId(), 0L),
                productCounts.getOrDefault(member.getId(), 0L),
                viewerId == null ? null : followingByViewer.contains(member.getId()))));
    }
}
