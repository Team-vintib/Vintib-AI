package com.ssafy.backend.social.repository;

import com.ssafy.backend.social.entity.Follow;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface FollowRepository extends JpaRepository<Follow, Long> {

    long countByFollowing_Id(Long memberId);

    boolean existsByFollower_IdAndFollowing_Id(Long followerId, Long followingId);

    void deleteByFollower_IdAndFollowing_Id(Long followerId, Long followingId);
}
