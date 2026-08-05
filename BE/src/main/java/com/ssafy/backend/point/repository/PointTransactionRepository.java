package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PointTransactionRepository extends JpaRepository<PointTransaction, Long> {

    /** 포인트 사용 내역 조회(MY-007) — 전체 원장. */
    Page<PointTransaction> findByMember_IdOrderByCreatedAtDesc(Long memberId, Pageable pageable);

    /** 출금 내역 조회(MY-007) — WITHDRAW 타입만 걸러 본다. */
    Page<PointTransaction> findByMember_IdAndTypeOrderByCreatedAtDesc(
            Long memberId, PointTransactionType type, Pageable pageable);
}