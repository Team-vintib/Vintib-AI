package com.ssafy.backend.point.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.client.TossPaymentConfirmResponse;
import com.ssafy.backend.global.client.TossPaymentsClient;
import com.ssafy.backend.global.config.TossPaymentsConfig.TossPaymentsProperties;
import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointChargeReadyResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.entity.PointCharge;
import com.ssafy.backend.point.entity.PointChargeStatus;
import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.point.repository.PointChargeRepository;
import com.ssafy.backend.point.repository.PointTransactionRepository;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class PointServiceTest {

    private static final Long MEMBER_ID = 1L;

    @Mock
    private PointAccountRepository pointAccountRepository;

    @Mock
    private PointTransactionRepository pointTransactionRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private PointChargeRepository pointChargeRepository;

    @Mock
    private TossPaymentsClient tossPaymentsClient;

    @Mock
    private Member member;

    private PointService pointService;

    @BeforeEach
    void setUp() {
        TossPaymentsProperties tossPaymentsProperties =
                new TossPaymentsProperties("https://api.tosspayments.com", "test_sk", "test_ck",
                        Duration.ofSeconds(1), Duration.ofSeconds(1));
        pointService = new PointService(pointAccountRepository, pointTransactionRepository, memberRepository,
                pointChargeRepository, tossPaymentsClient, tossPaymentsProperties);
    }

    private PointAccount newAccount() {
        return PointAccount.builder().member(member).build();
    }

    @Test
    void 계정이_없으면_잔액_조회시_0으로_생성된다() {
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.empty());
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(member));
        when(pointAccountRepository.save(any(PointAccount.class))).thenAnswer(invocation -> invocation.getArgument(0));

        PointBalanceResponse response = pointService.getBalance(MEMBER_ID);

        assertThat(response.available()).isZero();
        assertThat(response.bidHeld()).isZero();
    }

    @Test
    void 계정이_있으면_기존_잔액을_그대로_반환한다() {
        PointAccount account = newAccount();
        account.charge(50_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        PointBalanceResponse response = pointService.getBalance(MEMBER_ID);

        assertThat(response.available()).isEqualTo(50_000L);
    }

    @Test
    void 충전하면_available이_증가하고_원장에_기록된다() {
        PointAccount account = newAccount();
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        PointBalanceResponse response = pointService.charge(MEMBER_ID, 100_000L, null);

        assertThat(response.available()).isEqualTo(100_000L);
    }

    @Test
    void 잔액이_충분하면_출금신청시_available이_줄고_withdrawing이_늘어난다() {
        PointAccount account = newAccount();
        account.charge(100_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        PointBalanceResponse response = pointService.requestWithdrawal(MEMBER_ID, 30_000L);

        assertThat(response.available()).isEqualTo(70_000L);
        assertThat(response.withdrawing()).isEqualTo(30_000L);
    }

    @Test
    void 잔액이_부족하면_출금신청시_예외를_던진다() {
        PointAccount account = newAccount();
        account.charge(10_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        assertThatThrownBy(() -> pointService.requestWithdrawal(MEMBER_ID, 30_000L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INSUFFICIENT_POINTS);
    }

    @Test
    void 결제하면_available이_줄고_tradeEscrow로_보관된다() {
        PointAccount account = newAccount();
        account.charge(100_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        pointService.pay(MEMBER_ID, 60_000L, 10L);

        assertThat(account.getAvailable()).isEqualTo(40_000L);
        assertThat(account.getTradeEscrow()).isEqualTo(60_000L);
    }

    @Test
    void 결제시_잔액이_부족하면_예외를_던진다() {
        PointAccount account = newAccount();
        account.charge(10_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        assertThatThrownBy(() -> pointService.pay(MEMBER_ID, 60_000L, 10L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.INSUFFICIENT_POINTS);
    }

    @Test
    void 구매확정_정산시_구매자_tradeEscrow가_줄고_판매자_available이_늘어난다() {
        Long sellerId = 2L;
        Member seller = org.mockito.Mockito.mock(Member.class);

        PointAccount buyerAccount = newAccount();
        buyerAccount.charge(100_000L);
        buyerAccount.pay(60_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(buyerAccount));

        PointAccount sellerAccount = PointAccount.builder().member(seller).build();
        when(pointAccountRepository.findById(sellerId)).thenReturn(Optional.of(sellerAccount));

        pointService.settleOrder(MEMBER_ID, sellerId, 60_000L, 10L);

        assertThat(buyerAccount.getTradeEscrow()).isZero();
        assertThat(sellerAccount.getAvailable()).isEqualTo(60_000L);
    }

    @Test
    void 출금_내역_조회시_WITHDRAW_타입만_반환한다() {
        Pageable pageable = PageRequest.of(0, 20);
        PointTransaction withdrawal = PointTransaction.builder()
                .member(member)
                .type(PointTransactionType.WITHDRAW)
                .amount(-30_000L)
                .balanceAfter(70_000L)
                .build();
        when(pointTransactionRepository.findByMember_IdAndTypeOrderByCreatedAtDesc(
                MEMBER_ID, PointTransactionType.WITHDRAW, pageable))
                .thenReturn(new PageImpl<>(List.of(withdrawal), pageable, 1));

        PageResponse<PointTransactionResponse> response = pointService.getWithdrawals(MEMBER_ID, pageable);

        assertThat(response.content()).hasSize(1);
        assertThat(response.content().get(0).type()).isEqualTo("WITHDRAW");
    }

    @Test
    void 충전_준비하면_orderId를_발급하고_READY_상태로_저장한다() {
        PointAccount account = newAccount();
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        PointChargeReadyResponse response = pointService.readyCharge(MEMBER_ID, 100_000L);

        assertThat(response.orderId()).isNotBlank();
        assertThat(response.amount()).isEqualTo(100_000L);
        assertThat(response.clientKey()).isEqualTo("test_ck");
        verify(pointChargeRepository).save(any(PointCharge.class));
    }

    @Test
    void 승인하면_포인트가_적립되고_충전상태가_DONE이_된다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        PointCharge charge = PointCharge.builder().member(member).orderId("order-1").amount(100_000L).build();
        when(pointChargeRepository.findByOrderId("order-1")).thenReturn(Optional.of(charge));

        PointAccount account = newAccount();
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        TossPaymentConfirmResponse confirmed =
                new TossPaymentConfirmResponse("pk-1", "order-1", "DONE", 100_000L, OffsetDateTime.now());
        when(tossPaymentsClient.confirm("pk-1", "order-1", 100_000L)).thenReturn(confirmed);

        PointBalanceResponse response = pointService.confirmCharge(MEMBER_ID, "order-1", "pk-1", 100_000L);

        assertThat(response.available()).isEqualTo(100_000L);
        assertThat(charge.getStatus()).isEqualTo(PointChargeStatus.DONE);
    }

    @Test
    void 이미_완료된_충전을_다시_승인하면_재적립하지_않는다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        PointCharge charge = PointCharge.builder().member(member).orderId("order-1").amount(100_000L).build();
        charge.markDone("pk-1", LocalDateTime.now());
        when(pointChargeRepository.findByOrderId("order-1")).thenReturn(Optional.of(charge));

        PointAccount account = newAccount();
        account.charge(100_000L);
        when(pointAccountRepository.findById(MEMBER_ID)).thenReturn(Optional.of(account));

        PointBalanceResponse response = pointService.confirmCharge(MEMBER_ID, "order-1", "pk-1", 100_000L);

        assertThat(response.available()).isEqualTo(100_000L);
        verify(tossPaymentsClient, never()).confirm(any(), any(), any());
    }

    @Test
    void 준비_금액과_다르면_승인을_거부한다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        PointCharge charge = PointCharge.builder().member(member).orderId("order-1").amount(100_000L).build();
        when(pointChargeRepository.findByOrderId("order-1")).thenReturn(Optional.of(charge));

        assertThatThrownBy(() -> pointService.confirmCharge(MEMBER_ID, "order-1", "pk-1", 50_000L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PAYMENT_AMOUNT_MISMATCH);
        verify(tossPaymentsClient, never()).confirm(any(), any(), any());
    }

    @Test
    void 토스_승인이_실패하면_충전상태가_FAILED로_바뀌고_예외가_전파된다() {
        when(member.getId()).thenReturn(MEMBER_ID);
        PointCharge charge = PointCharge.builder().member(member).orderId("order-1").amount(100_000L).build();
        when(pointChargeRepository.findByOrderId("order-1")).thenReturn(Optional.of(charge));
        when(tossPaymentsClient.confirm("pk-1", "order-1", 100_000L))
                .thenThrow(new CustomException(ErrorCode.PAYMENT_CONFIRM_FAILED));

        assertThatThrownBy(() -> pointService.confirmCharge(MEMBER_ID, "order-1", "pk-1", 100_000L))
                .isInstanceOf(CustomException.class)
                .hasFieldOrPropertyWithValue("errorCode", ErrorCode.PAYMENT_CONFIRM_FAILED);
        assertThat(charge.getStatus()).isEqualTo(PointChargeStatus.FAILED);
    }
}
