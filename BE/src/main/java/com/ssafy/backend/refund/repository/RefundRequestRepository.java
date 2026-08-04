package com.ssafy.backend.refund.repository;

import com.ssafy.backend.refund.entity.RefundRequest;
import com.ssafy.backend.refund.entity.RefundStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RefundRequestRepository extends JpaRepository<RefundRequest, Long> {

    /** 환불 요청 목록 조회(REFUND-001) — 주문별 최신순. */
    List<RefundRequest> findByOrder_IdOrderByCreatedAtDesc(Long orderId);

    /** 중복 요청 방지 — 주문에 이미 진행 중인(REQUESTED) 요청이 있는지 확인한다. */
    Optional<RefundRequest> findFirstByOrder_IdAndStatus(Long orderId, RefundStatus status);
}