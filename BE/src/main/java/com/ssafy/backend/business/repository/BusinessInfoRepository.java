package com.ssafy.backend.business.repository;

import com.ssafy.backend.business.entity.BusinessInfo;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BusinessInfoRepository extends JpaRepository<BusinessInfo, Long> {
}
