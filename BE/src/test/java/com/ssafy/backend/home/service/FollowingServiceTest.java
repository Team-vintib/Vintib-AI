package com.ssafy.backend.home.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.home.dto.response.FollowedSellerResponse;
import com.ssafy.backend.home.dto.response.FollowingContentResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import com.ssafy.backend.member.entity.Member;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.port.SocialQueryPort;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductImageRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.social.entity.Follow;
import com.ssafy.backend.social.repository.FollowRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class FollowingServiceTest {

    private static final Long VIEWER_ID = 1L;
    private static final Long SELLER_ID = 2L;

    @Mock
    private FollowRepository followRepository;

    @Mock
    private ProductRepository productRepository;

    @Mock
    private ProductImageRepository productImageRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private BrandRepository brandRepository;

    @Mock
    private SocialQueryPort socialQueryPort;

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private LiveRepository liveRepository;

    @Mock
    private LiveCardAssembler liveCardAssembler;

    @Mock
    private Member seller;

    private FollowingService followingService;

    @BeforeEach
    void setUp() {
        AwsProperties awsProperties = new AwsProperties(
                "ap-northeast-2",
                "key",
                "secret",
                new AwsProperties.S3(null, null, "public-bucket", "private-bucket"));
        followingService = new FollowingService(
                followRepository,
                productRepository,
                productImageRepository,
                categoryRepository,
                brandRepository,
                socialQueryPort,
                s3StorageService,
                awsProperties,
                liveRepository,
                liveCardAssembler);
    }

    @Test
    void 팔로우한_판매자가_없으면_빈_콘텐츠를_반환하고_상품_조회는_하지_않는다() {
        when(followRepository.findByFollower_Id(eq(VIEWER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));

        FollowingContentResponse response = followingService.getFollowingContent(VIEWER_ID);

        assertThat(response.empty()).isTrue();
        assertThat(response.followedSellers()).isEmpty();
        assertThat(response.products()).isEmpty();
        assertThat(response.lives()).isEmpty();
        verify(productRepository, never())
                .findBySeller_IdInAndSaleStatusOrderByCreatedAtDesc(anyCollection(), any(), any());
    }

    @Test
    void 팔로우한_판매자의_ON_SALE_상품만_카드로_채워진다() {
        when(seller.getId()).thenReturn(SELLER_ID);
        when(seller.getNickname()).thenReturn("빈티지장인");
        when(seller.getProfileImageUrl()).thenReturn(null);

        Member viewerMember =
                Member.builder().email("viewer@example.com").password("encoded").name("조회자").build();
        Follow follow = Follow.builder().follower(viewerMember).following(seller).build();
        Pageable pageable = PageRequest.of(0, 10);
        when(followRepository.findByFollower_Id(eq(VIEWER_ID), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(follow), pageable, 1));
        when(followRepository.countFollowersByMemberIds(anyCollection())).thenReturn(List.of());
        when(productRepository.countBySellerIdsAndSaleStatusNot(anyCollection(), any())).thenReturn(List.of());

        Product product =
                Product.builder().seller(seller).categoryId(5L).title("폴로 램스울 니트").build();
        ReflectionTestUtils.setField(product, "id", 100L);
        product.registerDirectSale(39000L);
        when(productRepository.findBySeller_IdInAndSaleStatusOrderByCreatedAtDesc(
                        anyCollection(), eq(SaleStatus.ON_SALE), any()))
                .thenReturn(List.of(product));
        when(productImageRepository.findByProduct_IdInAndPrimaryTrue(anyCollection())).thenReturn(List.of());
        when(categoryRepository.findAllById(anyCollection())).thenReturn(List.of());
        when(brandRepository.findAllById(anyCollection())).thenReturn(List.of());
        when(socialQueryPort.isWishedBy(eq(100L), eq(VIEWER_ID))).thenReturn(true);

        FollowingContentResponse response = followingService.getFollowingContent(VIEWER_ID);

        assertThat(response.empty()).isFalse();
        assertThat(response.followedSellers()).hasSize(1);
        FollowedSellerResponse sellerResponse = response.followedSellers().get(0);
        assertThat(sellerResponse.sellerId()).isEqualTo(SELLER_ID);
        assertThat(sellerResponse.sellerName()).isEqualTo("빈티지장인");
        assertThat(sellerResponse.coverImageUrl()).isNull();
        assertThat(sellerResponse.liveId()).isNull();

        assertThat(response.products()).hasSize(1);
        ProductCardResponse productResponse = response.products().get(0);
        assertThat(productResponse.productId()).isEqualTo(100L);
        assertThat(productResponse.sellType()).isEqualTo("NORMAL");
        assertThat(productResponse.sellStatus()).isEqualTo("ON_SALE");
        assertThat(productResponse.price()).isEqualTo(39000L);
        assertThat(productResponse.isWished()).isTrue();

        assertThat(response.lives()).isEmpty();
    }
}
