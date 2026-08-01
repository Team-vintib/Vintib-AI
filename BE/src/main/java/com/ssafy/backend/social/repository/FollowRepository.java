package com.ssafy.backend.social.repository;

import com.ssafy.backend.social.entity.Follow;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface FollowRepository extends JpaRepository<Follow, Long> {

    long countByFollowing_Id(Long memberId);

    boolean existsByFollower_IdAndFollowing_Id(Long followerId, Long followingId);

    void deleteByFollower_IdAndFollowing_Id(Long followerId, Long followingId);

    /** 팔로워 목록(나를 팔로우하는 사람들) — 최신 팔로우순 페이징. */
    @EntityGraph(attributePaths = "follower")
    Page<Follow> findByFollowing_Id(Long followingId, Pageable pageable);

    /** 팔로잉 목록(내가 팔로우하는 사람들) — 최신 팔로우순 페이징. */
    @EntityGraph(attributePaths = "following")
    Page<Follow> findByFollower_Id(Long followerId, Pageable pageable);

    /** 여러 회원의 팔로워 수를 한 번에 센다 — 목록/홈 카드 응답에서 N+1을 피한다. */
    @Query("""
            SELECT f.following.id AS memberId, COUNT(f) AS count
            FROM Follow f
            WHERE f.following.id IN :memberIds
            GROUP BY f.following.id
            """)
    List<MemberFollowerCount> countFollowersByMemberIds(@Param("memberIds") Collection<Long> memberIds);

    /** 뷰어가 실제로 팔로우 중인 대상만 걸러낸다 — 목록 응답 isFollowing 배치 조회. */
    @Query("""
            SELECT f.following.id
            FROM Follow f
            WHERE f.follower.id = :viewerId AND f.following.id IN :targetIds
            """)
    Set<Long> findFollowingIdsAmong(@Param("viewerId") Long viewerId, @Param("targetIds") Collection<Long> targetIds);

    interface MemberFollowerCount {
        Long getMemberId();

        Long getCount();
    }
}
