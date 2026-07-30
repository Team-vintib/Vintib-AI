package com.ssafy.backend.product.repository;

import com.ssafy.backend.product.entity.Category;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CategoryRepository extends JpaRepository<Category, Long> {

    List<Category> findAllByOrderByIdAsc();

    /** 주어진 대분류들의 하위 소분류. 라이브 목록 카테고리 필터가 대분류를 하위까지 확장할 때 쓴다. */
    List<Category> findByParentIdIn(Collection<Long> parentIds);
}