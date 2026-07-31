package com.ssafy.backend.member.repository;

import com.ssafy.backend.member.entity.MemberInterestCategory;
import com.ssafy.backend.member.entity.MemberInterestCategoryId;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MemberInterestCategoryRepository extends JpaRepository<MemberInterestCategory, MemberInterestCategoryId> {

    List<MemberInterestCategory> findByMember_Id(Long memberId);

    // 전체 교체(PUT) 전 기존 관심 카테고리를 지운다.
    @Modifying
    @Query("delete from MemberInterestCategory c where c.member.id = :memberId")
    void deleteAllByMemberId(@Param("memberId") Long memberId);
}
