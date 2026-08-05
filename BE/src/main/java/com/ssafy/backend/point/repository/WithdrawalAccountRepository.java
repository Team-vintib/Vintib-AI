package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.WithdrawalAccount;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WithdrawalAccountRepository extends JpaRepository<WithdrawalAccount, Long> {
}