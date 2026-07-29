package com.ssafy.backend.wish.repository;

import com.ssafy.backend.wish.entity.Wish;
import com.ssafy.backend.wish.entity.WishId;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WishRepository extends JpaRepository<Wish, WishId> {
}
