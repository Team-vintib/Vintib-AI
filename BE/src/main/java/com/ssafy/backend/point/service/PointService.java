package com.ssafy.backend.point.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.point.repository.PointTransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 포인트 잔액 조회/충전/출금 신청(MY-007).
 *
 * <p>입찰 보류·거래 대금 보관·정산 대기 버킷은 경매/주문 실거래 트리거가 있어야 채워지는데,
 * 이번 범위엔 그 트리거가 없어 항상 0이다. 충전은 결제 연동 없는 테스트/데모 전용이고,
 * 출금은 신청까지만 처리한다 — 완료(관리자 승인)는 BIZ-001의 사업자 승인과 동일하게 범위 밖이라
 * DB를 직접 조작해야만 완료 처리된다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class PointService {

    private final PointAccountRepository pointAccountRepository;
    private final PointTransactionRepository pointTransactionRepository;
    private final MemberRepository memberRepository;

    // readOnly=true를 오버라이드한다 — 계정이 없으면 이 조회 안에서 0 잔액 행을 만들어야 하기 때문이다.
    @Transactional
    public PointBalanceResponse getBalance(Long memberId) {
        return PointBalanceResponse.from(getOrCreateAccount(memberId));
    }

    /** 포인트 사용 내역 조회(MY-007) — 전체 원장. */
    public PageResponse<PointTransactionResponse> getTransactions(Long memberId, Pageable pageable) {
        return PageResponse.from(pointTransactionRepository
                .findByMember_IdOrderByCreatedAtDesc(memberId, pageable)
                .map(PointTransactionResponse::from));
    }

    /** 출금 내역 조회(MY-007) — 원장에서 WITHDRAW 타입만 걸러 본다. */
    public PageResponse<PointTransactionResponse> getWithdrawals(Long memberId, Pageable pageable) {
        return PageResponse.from(pointTransactionRepository
                .findByMember_IdAndTypeOrderByCreatedAtDesc(memberId, PointTransactionType.WITHDRAW, pageable)
                .map(PointTransactionResponse::from));
    }

    @Transactional
    public PointBalanceResponse charge(Long memberId, Long amount) {
        PointAccount account = getOrCreateAccount(memberId);
        account.charge(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.CHARGE)
                .amount(amount)
                .balanceAfter(account.getAvailable())
                .build());
        return PointBalanceResponse.from(account);
    }

    @Transactional
    public PointBalanceResponse requestWithdrawal(Long memberId, Long amount) {
        PointAccount account = getOrCreateAccount(memberId);
        if (account.getAvailable() < amount) {
            throw new CustomException(ErrorCode.INSUFFICIENT_POINTS);
        }

        account.withdraw(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.WITHDRAW)
                .amount(-amount)
                .balanceAfter(account.getAvailable())
                .build());
        return PointBalanceResponse.from(account);
    }

    // 별도 회원가입 훅 대신 조회/충전/출금 시점에 없으면 0 잔액으로 만든다 — 가입 경로가
    // 여러 개여도 놓칠 위험이 없다.
    private PointAccount getOrCreateAccount(Long memberId) {
        return pointAccountRepository.findById(memberId)
                .orElseGet(() -> pointAccountRepository.save(PointAccount.builder()
                        .member(memberRepository.findById(memberId)
                                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND)))
                        .build()));
    }
}
