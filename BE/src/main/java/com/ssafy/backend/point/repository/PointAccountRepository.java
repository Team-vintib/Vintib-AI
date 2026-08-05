package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.PointAccount;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PointAccountRepository extends JpaRepository<PointAccount, Long> {

    /**
     * 잔액 증감을 위한 행 잠금 조회(AUCT-007~009).
     *
     * <p>경매 행 잠금({@code AuctionRepository.findByIdForUpdate})이 같은 경매의 입찰을
     * 직렬화하지만, 한 회원이 <b>서로 다른 경매</b>에 동시에 입찰을 시도하면 그 잠금만으로는
     * 막히지 않는다 — 이 경우 두 트랜잭션이 같은 {@code point_account} 행을 동시에 건드릴 수
     * 있다. 여기서 잠가야 "잔액 확인 → 차감"이 원자적이다.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM PointAccount a WHERE a.memberId = :memberId")
    Optional<PointAccount> findWithLockByMemberId(@Param("memberId") Long memberId);
}
