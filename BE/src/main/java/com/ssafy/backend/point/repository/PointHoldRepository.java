package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.PointHold;
import com.ssafy.backend.point.entity.PointHoldStatus;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PointHoldRepository extends JpaRepository<PointHold, Long> {

    /**
     * 이 회원이 지금 어딘가에서 최고 입찰자로 쥐고 있는 보류(있다면 전체 경매를 통틀어 최대 1건).
     *
     * <p>AUCT-009 사전 체크에 쓴다 — 애플리케이션이 먼저 걸러 명확한 에러를 주고,
     * {@code ux_point_hold_member_active}는 그 사이 경합이 생겼을 때의 최후 방어선이다.
     */
    Optional<PointHold> findByMember_IdAndStatus(Long memberId, PointHoldStatus status);

    /** 이 경매의 현재 최고 입찰자가 쥔 보류. 상위 입찰이 들어와 해제할 때 찾는다. */
    Optional<PointHold> findByAuctionIdAndStatus(Long auctionId, PointHoldStatus status);
}
