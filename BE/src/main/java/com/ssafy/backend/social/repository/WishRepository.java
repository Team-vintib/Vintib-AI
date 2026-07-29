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
}
