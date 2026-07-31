package com.ssafy.backend.member.repository;

import com.ssafy.backend.member.entity.MemberInterestBrand;
import com.ssafy.backend.member.entity.MemberInterestBrandId;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MemberInterestBrandRepository extends JpaRepository<MemberInterestBrand, MemberInterestBrandId> {

    List<MemberInterestBrand> findByMember_Id(Long memberId);

    // 전체 교체(PUT) 전 기존 관심 브랜드를 지운다.
    @Modifying
    @Query("delete from MemberInterestBrand b where b.member.id = :memberId")
    void deleteAllByMemberId(@Param("memberId") Long memberId);
}
