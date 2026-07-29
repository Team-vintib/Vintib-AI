package com.ssafy.backend.wish.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.member.repository.MemberRepository;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.wish.dto.response.WishResponse;
import com.ssafy.backend.wish.entity.Wish;
import com.ssafy.backend.wish.entity.WishId;
import com.ssafy.backend.wish.repository.WishRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class WishServiceTest {

    private static final Long MEMBER_ID = 1L;
    private static final Long PRODUCT_ID = 10L;

    @Mock
    private WishRepository wishRepository;

    @Mock
    private MemberRepository memberRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private Member seller;

    @Mock
    private Member wisher;

    private WishService wishService;
    private Product product;

    @BeforeEach
    void setUp() {
        wishService = new WishService(wishRepository, memberRepository, productRepository);
        product = Product.builder().seller(seller).title("빈티지 자켓").build();
        ReflectionTestUtils.setField(product, "id", PRODUCT_ID);
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.ON_SALE);
    }

    @Test
    void 찜에_성공한다() {
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(wishRepository.existsById(new WishId(MEMBER_ID, PRODUCT_ID))).thenReturn(false);
        when(memberRepository.findById(MEMBER_ID)).thenReturn(Optional.of(wisher));
        when(wisher.getId()).thenReturn(MEMBER_ID);
        when(wishRepository.save(any(Wish.class))).thenAnswer(invocation -> invocation.getArgument(0));

        WishResponse response = wishService.wish(MEMBER_ID, PRODUCT_ID);

        assertThat(response.productId()).isEqualTo(PRODUCT_ID);
    }

    @Test
    void 이미_찜한_상품이면_예외를_던진다() {
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));
        when(wishRepository.existsById(new WishId(MEMBER_ID, PRODUCT_ID))).thenReturn(true);

        assertThatThrownBy(() -> wishService.wish(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.WISH_ALREADY_EXISTS);
    }

    @Test
    void 존재하지_않는_상품을_찜하면_예외를_던진다() {
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> wishService.wish(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 비공개_상품을_찜하면_예외를_던진다() {
        ReflectionTestUtils.setField(product, "saleStatus", SaleStatus.PRIVATE);
        when(productRepository.findById(PRODUCT_ID)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> wishService.wish(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.PRODUCT_NOT_FOUND);
    }

    @Test
    void 찜_해제에_성공한다() {
        WishId wishId = new WishId(MEMBER_ID, PRODUCT_ID);
        when(wishRepository.existsById(wishId)).thenReturn(true);

        wishService.unwish(MEMBER_ID, PRODUCT_ID);

        verify(wishRepository).deleteById(wishId);
    }

    @Test
    void 찜하지_않은_상품을_해제하면_예외를_던진다() {
        when(wishRepository.existsById(new WishId(MEMBER_ID, PRODUCT_ID))).thenReturn(false);

        assertThatThrownBy(() -> wishService.unwish(MEMBER_ID, PRODUCT_ID))
                .isInstanceOf(CustomException.class)
                .extracting(e -> ((CustomException) e).getErrorCode())
                .isEqualTo(ErrorCode.WISH_NOT_FOUND);
    }
}
