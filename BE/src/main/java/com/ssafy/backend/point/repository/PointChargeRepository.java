package com.ssafy.backend.point.repository;

import com.ssafy.backend.point.entity.PointCharge;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PointChargeRepository extends JpaRepository<PointCharge, Long> {

    Optional<PointCharge> findByOrderId(String orderId);
}