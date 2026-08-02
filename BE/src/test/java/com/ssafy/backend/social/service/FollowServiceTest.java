package com.ssafy.backend.social.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.dto.response.FollowResponse;
import com.ssafy.backend.social.dto.response.FollowUserResponse;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class FollowServiceTest {

    private static final Long FOLLOWER_ID = 1L;
    private static final Long TARGET_ID = 2L;

    @Mock
    private FollowRepository followRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private Member follower;

    @Mock
    private Member target;

    private FollowService followService;

    @BeforeEach
    void setUp() {
        followService = new FollowService(followRepository, memberRepository, productRepository);
    }

    @Test
    void 팔로우에_성공한다() {
        when(followRepository.existsByFollower_IdAndFollowing_Id(FOLLOWER_ID, TARGET_ID)).thenReturn(false);
        when(memberRepository.findById(FOLLOWER_ID)).thenReturn(Optional.of(follower));
        when(memberRepository.findById(TARGET_ID)).thenReturn(Optional.of(target));
        when(followRepository.countByFollowing_Id(TARGET_ID)).thenReturn(1L);

        FollowResponse response = followService.follow(FOLLOWER_ID, TARGET_ID);

        assertThat(response.targetUserId()).isEqualTo(TARGET_ID);
        assertThat(response.isFollowing()).isTrue();
        assertThat(response.followerCount()).isEqualTo(1L);
    }

    @Test
    void 이미_팔로우_중이면_저장_없이_현재_상태를_반환한다() {
        when(followRepository.existsByFollower_IdAndFollowing_Id(FOLLOWER_ID, TARGET_ID)).thenReturn(true);
        when(followRepository.countByFollowing_Id(TARGET_ID)).thenReturn(5L);

        FollowResponse response = followService.follow(FOLLOWER_ID, TARGET_ID);

        assertThat(response.isFollowing()).isTrue();
        assertThat(response.followerCount()).isEqualTo(5L);
        verify(followRepository, never()).save(any(Follow.class));
        verify(memberRepository, never()).findById(any());
    }

    @Test
    void 자기_자신을_팔로우하면_예외를_던진다() {
        assertThatThrownBy(() -> followService.follow(FOLLOWER_ID, FOLLOWER_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.SELF_FOLLOW_NOT_ALLOWED);
    }

    @Test
    void 존재하지_않는_회원을_팔로우하면_예외를_던진다() {
        when(followRepository.existsByFollower_IdAndFollowing_Id(FOLLOWER_ID, TARGET_ID)).thenReturn(false);
        when(memberRepository.findById(FOLLOWER_ID)).thenReturn(Optional.of(follower));
        when(memberRepository.findById(TARGET_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> followService.follow(FOLLOWER_ID, TARGET_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.USER_NOT_FOUND);
    }

    @Test
    void 팔로우_해제에_성공한다() {
        followService.unfollow(FOLLOWER_ID, TARGET_ID);

        verify(followRepository).deleteByFollower_IdAndFollowing_Id(FOLLOWER_ID, TARGET_ID);
    }

    @Test
    void 팔로우하지_않은_상태에서_해제해도_예외없이_성공한다() {
        followService.unfollow(FOLLOWER_ID, TARGET_ID);

        verify(followRepository).deleteByFollower_IdAndFollowing_Id(FOLLOWER_ID, TARGET_ID);
    }

    @Test
    void 팔로워_목록을_최신순으로_반환한다() {
        when(memberRepository.existsById(TARGET_ID)).thenReturn(true);
        when(follower.getId()).thenReturn(FOLLOWER_ID);
        when(follower.getNickname()).thenReturn("follower-nick");
        Follow follow = Follow.builder().follower(follower).following(target).build();
        Pageable pageable = PageRequest.of(0, 20);
        when(followRepository.findByFollowing_Id(eq(TARGET_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(follow), pageable, 1));
        when(followRepository.countFollowersByMemberIds(anyCollection())).thenReturn(List.of());
        when(productRepository.countBySellerIdsAndSaleStatusNot(anyCollection(), any())).thenReturn(List.of());

        PageResponse<FollowUserResponse> response = followService.getFollowers(TARGET_ID, null, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).id()).isEqualTo(FOLLOWER_ID);
    }

    @Test
    void 비회원이_조회하면_isFollowing이_false다() {
        when(memberRepository.existsById(TARGET_ID)).thenReturn(true);
        when(follower.getId()).thenReturn(FOLLOWER_ID);
        Follow follow = Follow.builder().follower(follower).following(target).build();
        Pageable pageable = PageRequest.of(0, 20);
        when(followRepository.findByFollowing_Id(eq(TARGET_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(follow), pageable, 1));
        when(followRepository.countFollowersByMemberIds(anyCollection())).thenReturn(List.of());
        when(productRepository.countBySellerIdsAndSaleStatusNot(anyCollection(), any())).thenReturn(List.of());

        PageResponse<FollowUserResponse> response = followService.getFollowers(TARGET_ID, null, pageable);

        assertThat(response.content().get(0).isFollowing()).isFalse();
        verify(followRepository, never()).findFollowingIdsAmong(any(), anyCollection());
    }

    @Test
    void 로그인_회원이_조회하면_isFollowing이_채워진다() {
        Long viewerId = 99L;
        when(memberRepository.existsById(TARGET_ID)).thenReturn(true);
        when(follower.getId()).thenReturn(FOLLOWER_ID);
        Follow follow = Follow.builder().follower(follower).following(target).build();
        Pageable pageable = PageRequest.of(0, 20);
        when(followRepository.findByFollowing_Id(eq(TARGET_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(follow), pageable, 1));
        when(followRepository.countFollowersByMemberIds(anyCollection())).thenReturn(List.of());
        when(productRepository.countBySellerIdsAndSaleStatusNot(anyCollection(), any())).thenReturn(List.of());
        when(followRepository.findFollowingIdsAmong(eq(viewerId), anyCollection()))
                .thenReturn(java.util.Set.of(FOLLOWER_ID));

        PageResponse<FollowUserResponse> response = followService.getFollowers(TARGET_ID, viewerId, pageable);

        assertThat(response.content().get(0).isFollowing()).isTrue();
    }

    @Test
    void 존재하지_않는_회원의_팔로워_목록을_조회하면_예외를_던진다() {
        when(memberRepository.existsById(TARGET_ID)).thenReturn(false);
        Pageable pageable = PageRequest.of(0, 20);

        assertThatThrownBy(() -> followService.getFollowers(TARGET_ID, null, pageable))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.USER_NOT_FOUND);
    }
}
