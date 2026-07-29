package com.ssafy.backend.wish.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.wish.dto.response.WishResponse;
import com.ssafy.backend.wish.entity.Wish;
import com.ssafy.backend.wish.entity.WishId;
import com.ssafy.backend.wish.repository.WishRepository;
import lombok.RequiredArgsConstructor;
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
                .filter(p -> !p.isPrivate())
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
}
