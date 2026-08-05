package com.ssafy.backend.social.repository;

import com.ssafy.backend.social.entity.Wish;
import com.ssafy.backend.social.entity.WishId;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WishRepository extends JpaRepository<Wish, WishId> {

    @EntityGraph(attributePaths = "product")
    Page<Wish> findByMember_Id(Long memberId, Pageable pageable);

    /** 마이페이지 요약(에픽 S15P11A108-207 보너스) — 찜한 상품 수. */
    long countByMember_Id(Long memberId);
}
