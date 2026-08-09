package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.SimilarProductCandidate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SimilarProductCandidateRepository extends JpaRepository<SimilarProductCandidate, Long> {

    List<SimilarProductCandidate> findByProductIdOrderByRankAsc(Long productId);

    // 배치가 갱신할 때마다 그 상품의 기존 후보를 전부 지우고 새로 넣는다(upsert-by-replace).
    @Modifying
    @Query("delete from SimilarProductCandidate c where c.productId = :productId")
    void deleteByProductId(@Param("productId") Long productId);
}
