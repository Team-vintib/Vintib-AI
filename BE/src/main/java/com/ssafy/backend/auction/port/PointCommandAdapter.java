package com.ssafy.backend.auction.port;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.entity.PointHold;
import com.ssafy.backend.point.entity.PointHoldStatus;
import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.point.repository.PointHoldRepository;
import com.ssafy.backend.point.repository.PointTransactionRepository;
import java.time.LocalDateTime;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;

/**
 * {@link PointCommandPort}의 유일한 구현. 포인트 도메인에 대한 의존을 이 파일 하나로 묶는다.
 *
 * <p><b>회원별 {@code point_hold} 활성 보류는 사전 조회 + INSERT 실패 시 변환, 이중으로
 * 막는다</b> — {@code AuthService.signUp}이 이메일 유니크를 다루는 것과 같은 패턴이다.
 * 사전 조회는 흔한 경로(같은 회원이 진짜로 다른 경매에 이미 참여 중)를 깔끔한 에러로
 * 걸러내고, {@code ux_point_hold_member_active} 유니크 위반 캐치는 그 사이 경합이 생긴
 * 드문 경로의 최후 방어선이다.
 *
 * <p>⚠️ <b>캐치 후에는 아무 것도 더 하지 않고 즉시 던진다.</b> PostgreSQL은 트랜잭션 안에서
 * 한 문장이라도 실패하면 그 트랜잭션을 롤백 전까지 통째로 못 쓰게 만든다 — 캐치하고
 * "성공"으로 계속 진행하면 커밋 시점에 {@code UnexpectedRollbackException}이 터진다.
 */
@Component
@RequiredArgsConstructor
public class PointCommandAdapter implements PointCommandPort {

    private static final String REF_TYPE_AUCTION = "AUCTION";
    // PointService.pay 가 주문 결제에 쓰는 것과 같은 값 — 낙찰 결제도 같은 원장에서 읽힌다.
    private static final String REF_TYPE_ORDER = "ORDER";

    private final PointAccountRepository pointAccountRepository;
    private final PointHoldRepository pointHoldRepository;
    private final PointTransactionRepository pointTransactionRepository;
    private final MemberRepository memberRepository;

    @Override
    public void holdForBid(Long memberId, Long auctionId, Long bidId, long amount) {
        if (pointHoldRepository.findByMember_IdAndStatus(memberId, PointHoldStatus.HELD).isPresent()) {
            throw new CustomException(ErrorCode.ACTIVE_HOLD_ELSEWHERE);
        }

        PointAccount account = getOrCreateAccountWithLock(memberId);
        if (!account.hasEnoughAvailable(amount)) {
            throw new CustomException(ErrorCode.INSUFFICIENT_POINTS);
        }

        account.holdForBid(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.BID_HOLD)
                .amount(-amount)
                .balanceAfter(account.getAvailable())
                .refType(REF_TYPE_AUCTION)
                .refId(auctionId)
                .build());

        try {
            pointHoldRepository.saveAndFlush(
                    PointHold.hold(account.getMember(), auctionId, bidId, amount, LocalDateTime.now()));
        } catch (DataIntegrityViolationException raceOnActiveHold) {
            // 사전 조회와 이 INSERT 사이에 다른 요청이 먼저 보류를 잡았다. 트랜잭션은 이미
            // 못 쓰는 상태이므로 더 이상 아무 쿼리도 시도하지 않고 그대로 던진다.
            throw new CustomException(ErrorCode.ACTIVE_HOLD_ELSEWHERE);
        }
    }

    @Override
    public void releaseHoldForAuction(Long auctionId) {
        pointHoldRepository.findByAuctionIdAndStatus(auctionId, PointHoldStatus.HELD)
                .ifPresent(hold -> {
                    LocalDateTime now = LocalDateTime.now();
                    hold.release(now);

                    PointAccount account = getOrCreateAccountWithLock(hold.getMember().getId());
                    account.releaseHold(hold.getAmount());
                    pointTransactionRepository.save(PointTransaction.builder()
                            .member(account.getMember())
                            .type(PointTransactionType.BID_RELEASE)
                            .amount(hold.getAmount())
                            .balanceAfter(account.getAvailable())
                            .refType(REF_TYPE_AUCTION)
                            .refId(auctionId)
                            .build());
                });
    }

    @Override
    public void convertHoldToPayment(Long auctionId, Long orderId) {
        pointHoldRepository.findByAuctionIdAndStatus(auctionId, PointHoldStatus.HELD)
                .ifPresent(hold -> {
                    LocalDateTime now = LocalDateTime.now();
                    hold.convert(now);

                    PointAccount account = getOrCreateAccountWithLock(hold.getMember().getId());
                    long amount = hold.getAmount();

                    // 보류를 먼저 잔액으로 되돌린 뒤 결제한다. 버킷을 건너뛰고 bidHeld → tradeEscrow
                    // 로 바로 옮기는 메서드를 새로 만들 수도 있지만, 그러면 원장의 balanceAfter 가
                    // 중간 상태를 건너뛰어 잔액 추적이 끊긴다.
                    account.releaseHold(amount);
                    pointTransactionRepository.save(PointTransaction.builder()
                            .member(account.getMember())
                            .type(PointTransactionType.BID_RELEASE)
                            .amount(amount)
                            .balanceAfter(account.getAvailable())
                            .refType(REF_TYPE_AUCTION)
                            .refId(auctionId)
                            .build());

                    account.pay(amount);
                    pointTransactionRepository.save(PointTransaction.builder()
                            .member(account.getMember())
                            .type(PointTransactionType.PAYMENT)
                            .amount(-amount)
                            .balanceAfter(account.getAvailable())
                            .refType(REF_TYPE_ORDER)
                            .refId(orderId)
                            .build());
                });
    }

    // point 계좌가 없으면(한 번도 충전/입찰한 적 없는 회원) 0 잔액으로 만든다 — PointService의
    // getOrCreateAccount와 같은 정책이다. 여기서는 잠금이 필요해 별도로 조회한다.
    private PointAccount getOrCreateAccountWithLock(Long memberId) {
        return pointAccountRepository.findWithLockByMemberId(memberId)
                .orElseGet(() -> pointAccountRepository.save(PointAccount.builder()
                        .member(memberRepository.findById(memberId)
                                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND)))
                        .build()));
    }
}
