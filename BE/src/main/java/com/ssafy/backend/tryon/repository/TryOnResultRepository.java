package com.ssafy.backend.tryon.repository;

import com.ssafy.backend.tryon.entity.TryOnResult;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TryOnResultRepository extends JpaRepository<TryOnResult, Long> {

    List<TryOnResult> findAllByMemberIdAndDeletedAtIsNullOrderByCreatedAtDesc(Long memberId);
}