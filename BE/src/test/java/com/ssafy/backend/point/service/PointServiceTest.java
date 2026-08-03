package com.ssafy.backend.point.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.point.dto.response.PointBalanceResponse;
import com.ssafy.backend.point.dto.response.PointTransactionResponse;
import com.ssafy.backend.point.entity.PointAccount;
import com.ssafy.backend.point.entity.PointTransaction;
import com.ssafy.backend.point.entity.PointTransactionType;
import com.ssafy.backend.point.repository.PointAccountRepository;
import com.ssafy.backend.point.repository.PointTransactionRepository;
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
    private Member member;

    private PointService pointService;

    @BeforeEach
    void setUp() {
        pointService = new PointService(pointAccountRepository, pointTransactionRepository, memberRepository);
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

        PointBalanceResponse response = pointService.charge(MEMBER_ID, 100_000L);

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
}
