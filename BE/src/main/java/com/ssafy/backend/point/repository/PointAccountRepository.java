package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.PointAccount;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PointAccountRepository extends JpaRepository<PointAccount, Long> {
}
