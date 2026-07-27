package com.ssafy.backend.auction.repository;

import com.ssafy.backend.auction.entity.Auction;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuctionRepository extends JpaRepository<Auction, Long> {
}