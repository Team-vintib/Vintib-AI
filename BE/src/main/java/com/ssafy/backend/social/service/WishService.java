package com.ssafy.backend.social.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.global.response.PageResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.social.dto.response.WishItemResponse;
import com.ssafy.backend.social.dto.response.WishResponse;
import com.ssafy.backend.social.entity.Wish;
import com.ssafy.backend.social.entity.WishId;
import com.ssafy.backend.social.repository.WishRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class WishService {

    private final WishRepository wishRepository;
    private final MemberRepository memberRepository;
    private final ProductRepository productRepository;

    @Transactional
    public WishResponse wish(Long memberId, Long productId) {
        Product product = productRepository.findById(productId)
                .filter(p -> !p.isDraft())
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));

        WishId wishId = new WishId(memberId, productId);
        if (wishRepository.existsById(wishId)) {
            throw new CustomException(ErrorCode.WISH_ALREADY_EXISTS);
        }

        Member member = memberRepository.findById(memberId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        Wish wish = wishRepository.save(Wish.builder().member(member).product(product).build());
        return WishResponse.of(wish);
    }

    @Transactional
    public void unwish(Long memberId, Long productId) {
        WishId wishId = new WishId(memberId, productId);
        if (!wishRepository.existsById(wishId)) {
            throw new CustomException(ErrorCode.WISH_NOT_FOUND);
        }
        wishRepository.deleteById(wishId);
    }

    public PageResponse<WishItemResponse> getWishList(Long memberId, Pageable pageable) {
        // 찜한 시각 최신순 고정 — 클라이언트가 다른 sort를 보내도 무시한다(ProductService.getProductList와 동일한 정책).
        Pageable sortedByLatest = PageRequest.of(
                pageable.getPageNumber(), pageable.getPageSize(), Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Wish> wishes = wishRepository.findByMember_Id(memberId, sortedByLatest);
        return PageResponse.from(wishes.map(WishItemResponse::of));
    }
}
