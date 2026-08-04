package com.ssafy.backend.point.service;

import com.ssafy.backend.global.client.TossPaymentConfirmResponse;
import com.ssafy.backend.global.client.TossPaymentsClient;
import com.ssafy.backend.global.config.TossPaymentsConfig.TossPaymentsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointChargeReadyResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
import com.ssafy.backend.point.dto.response.WithdrawalAccountResponse;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.entity.PointCharge;
import com.ssafy.backend.point.entity.PointChargeStatus;
import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import com.ssafy.backend.point.entity.WithdrawalAccount;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.point.repository.PointChargeRepository;
import com.ssafy.backend.point.repository.PointTransactionRepository;
import com.ssafy.backend.point.repository.WithdrawalAccountRepository;
import java.time.LocalDateTime;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 포인트 잔액 조회/충전/출금 신청(MY-007), 주문 결제·정산({@link #pay}/{@link #settleOrder}, SALE-002/ORDER-002/003),
 * 환불 승인 시 구매자 환급({@link #refundOrder}, REFUND-002).
 *
 * <p>입찰 보류(bidHeld)는 경매 입찰 자체가 아직 없어(AUCT-003 이후) 이번 범위에서도 항상 0이다.
 * 정산 대기(settling)도 관리자 승인·정산 주기 절차가 정의되지 않아 쓰지 않는다 — 구매 확정 시
 * 판매자 available로 바로 정산한다. 충전은 토스페이먼츠 결제위젯 준비({@link #readyCharge})/승인
 * ({@link #confirmCharge}) 2단계로 처리한다(POINT-001). 출금은 신청까지만 처리한다 — 완료(관리자
 * 승인)는 BIZ-001의 사업자 승인과 동일하게 범위 밖이라 DB를 직접 조작해야만 완료 처리된다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class PointService {

    private final PointAccountRepository pointAccountRepository;
    private final PointTransactionRepository pointTransactionRepository;
    private final MemberRepository memberRepository;
    private final PointChargeRepository pointChargeRepository;
    private final TossPaymentsClient tossPaymentsClient;
    private final TossPaymentsProperties tossPaymentsProperties;
    private final WithdrawalAccountRepository withdrawalAccountRepository;

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
    public PointBalanceResponse charge(Long memberId, Long amount, Long chargeRefId) {
        PointAccount account = getOrCreateAccount(memberId);
        account.charge(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.CHARGE)
                .amount(amount)
                .balanceAfter(account.getAvailable())
                .refType("POINT_CHARGE")
                .refId(chargeRefId)
                .build());
        return PointBalanceResponse.from(account);
    }

    /** 충전 준비(POINT-001) — 결제위젯에 넘길 orderId를 발급하고 PointCharge를 READY로 저장한다. */
    @Transactional
    public PointChargeReadyResponse readyCharge(Long memberId, Long amount) {
        PointAccount account = getOrCreateAccount(memberId);
        String orderId = UUID.randomUUID().toString();
        pointChargeRepository.save(PointCharge.builder()
                .member(account.getMember())
                .orderId(orderId)
                .amount(amount)
                .build());
        return new PointChargeReadyResponse(orderId, amount, tossPaymentsProperties.clientKey());
    }

    /** 충전 승인(POINT-001) — 토스 결제 승인 후 포인트를 적립한다. 중복 confirm 호출에도 안전(idempotent)하다. */
    @Transactional
    public PointBalanceResponse confirmCharge(Long memberId, String orderId, String paymentKey, Long amount) {
        PointCharge charge = pointChargeRepository.findByOrderId(orderId)
                .orElseThrow(() -> new CustomException(ErrorCode.PAYMENT_CHARGE_NOT_FOUND));
        // 다른 회원 소유 orderId로 시도하는 경우 존재 자체를 드러내지 않는다(IDOR 방지).
        if (!charge.getMember().getId().equals(memberId)) {
            throw new CustomException(ErrorCode.PAYMENT_CHARGE_NOT_FOUND);
        }
        if (charge.getStatus() == PointChargeStatus.DONE) {
            return getBalance(memberId);
        }
        if (charge.getStatus() != PointChargeStatus.READY) {
            throw new CustomException(ErrorCode.PAYMENT_ALREADY_PROCESSED);
        }
        if (!charge.getAmount().equals(amount)) {
            throw new CustomException(ErrorCode.PAYMENT_AMOUNT_MISMATCH);
        }

        TossPaymentConfirmResponse confirmed;
        try {
            confirmed = tossPaymentsClient.confirm(paymentKey, orderId, amount);
        } catch (CustomException e) {
            charge.markFailed();
            throw e;
        }

        charge.markDone(
                paymentKey,
                confirmed.approvedAt() != null ? confirmed.approvedAt().toLocalDateTime() : LocalDateTime.now());
        return charge(memberId, amount, charge.getId());
    }

    /** 상시 판매 즉시구매 결제(SALE-002) — available 부족 시 거부, 성공하면 tradeEscrow로 보관한다. */
    @Transactional
    public void pay(Long buyerId, Long amount, Long orderId) {
        PointAccount account = getOrCreateAccount(buyerId);
        if (account.getAvailable() < amount) {
            throw new CustomException(ErrorCode.INSUFFICIENT_POINTS);
        }

        account.pay(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.PAYMENT)
                .amount(-amount)
                .balanceAfter(account.getAvailable())
                .refType("ORDER")
                .refId(orderId)
                .build());
    }

    /**
     * 구매 확정 정산(ORDER-002/003) — 구매자의 보관 잔액을 내보내고 판매자에게 바로 정산한다.
     * 정산 대기(settling) 절차가 없어 판매자 원장만 남긴다(구매자 측은 결제 시점 PAYMENT 기록으로 충분).
     */
    @Transactional
    public void settleOrder(Long buyerId, Long sellerId, Long amount, Long orderId) {
        getOrCreateAccount(buyerId).releaseEscrow(amount);
        PointAccount sellerAccount = getOrCreateAccount(sellerId);
        sellerAccount.settle(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(sellerAccount.getMember())
                .type(PointTransactionType.SETTLEMENT)
                .amount(amount)
                .balanceAfter(sellerAccount.getAvailable())
                .refType("ORDER")
                .refId(orderId)
                .build());
    }

    /**
     * 환불 승인 정산(REFUND-002) — 보관 중이던 대금을 판매자에게 정산하지 않고 구매자 available로
     * 돌려준다. {@link #settleOrder}와 달리 판매자 측 반영이 없다.
     */
    @Transactional
    public void refundOrder(Long buyerId, Long amount, Long orderId) {
        PointAccount account = getOrCreateAccount(buyerId);
        account.refund(amount);
        pointTransactionRepository.save(PointTransaction.builder()
                .member(account.getMember())
                .type(PointTransactionType.REFUND)
                .amount(amount)
                .balanceAfter(account.getAvailable())
                .refType("ORDER")
                .refId(orderId)
                .build());
    }

    @Transactional
    public PointBalanceResponse requestWithdrawal(Long memberId, Long amount) {
        if (withdrawalAccountRepository.findById(memberId).isEmpty()) {
            throw new CustomException(ErrorCode.WITHDRAWAL_ACCOUNT_REQUIRED);
        }

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

    /** 출금 계좌 등록/수정(POINT-003) — upsert. 없으면 새로 만들고, 있으면 갱신한다. */
    @Transactional
    public WithdrawalAccountResponse registerWithdrawalAccount(
            Long memberId, String bankName, String accountNumber, String accountHolderName) {
        WithdrawalAccount account = withdrawalAccountRepository.findById(memberId).orElse(null);
        if (account == null) {
            account = withdrawalAccountRepository.save(WithdrawalAccount.builder()
                    .member(getOrCreateAccount(memberId).getMember())
                    .bankName(bankName)
                    .accountNumber(accountNumber)
                    .accountHolderName(accountHolderName)
                    .build());
        } else {
            account.updateAccount(bankName, accountNumber, accountHolderName);
        }
        return WithdrawalAccountResponse.from(account);
    }

    /** 출금 계좌 조회(POINT-003). */
    public WithdrawalAccountResponse getWithdrawalAccount(Long memberId) {
        WithdrawalAccount account = withdrawalAccountRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.WITHDRAWAL_ACCOUNT_NOT_FOUND));
        return WithdrawalAccountResponse.from(account);
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