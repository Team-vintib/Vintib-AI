package com.ssafy.backend.live.repository;

import com.ssafy.backend.live.entity.Live;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiveRepository extends JpaRepository<Live, Long> {
}