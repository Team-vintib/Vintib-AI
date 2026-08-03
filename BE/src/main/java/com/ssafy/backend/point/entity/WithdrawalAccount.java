package com.ssafy.backend.point.entity;

import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapsId;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 출금(현금화) 계좌 정보(POINT-003). {@code PointAccount}와 같은 공유 PK 1:1
 * 구조 — 회원당 한 행만 존재한다. 실제 은행 송금 연동은 범위 밖이라 계좌 정보만 남긴다.
 */
@Entity
@Table(name = "withdrawal_account")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WithdrawalAccount {

    @Id
    private Long memberId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id")
    private Member member;

    @Column(name = "bank_name", nullable = false, length = 50)
    private String bankName;

    @Column(name = "account_number", nullable = false, length = 30)
    private String accountNumber;

    @Column(name = "account_holder_name", nullable = false, length = 50)
    private String accountHolderName;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Builder
    private WithdrawalAccount(Member member, String bankName, String accountNumber, String accountHolderName) {
        this.member = member;
        this.bankName = bankName;
        this.accountNumber = accountNumber;
        this.accountHolderName = accountHolderName;
        this.updatedAt = LocalDateTime.now();
    }

    /** 출금 계좌 등록/수정(POINT-003). */
    public void updateAccount(String bankName, String accountNumber, String accountHolderName) {
        this.bankName = bankName;
        this.accountNumber = accountNumber;
        this.accountHolderName = accountHolderName;
        this.updatedAt = LocalDateTime.now();
    }
}
