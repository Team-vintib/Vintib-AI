package com.ssafy.backend.home.service;

import com.ssafy.backend.home.dto.response.CategoryProductSectionResponse;
import com.ssafy.backend.home.dto.response.HomeContentResponse;
import com.ssafy.backend.home.dto.response.LiveCardResponse;
import com.ssafy.backend.home.dto.response.ProductCardResponse;
import com.ssafy.backend.home.repository.HomeProductQueryRepository;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveStatus;
import com.ssafy.backend.live.repository.LiveRepository;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.entity.SaleStatus;
import com.ssafy.backend.product.repository.CategoryRepository;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 홈 콘텐츠 조회 서비스.
 *
 * <p><b>모든 섹션이 실데이터다.</b> 이전에는 전부 Mock이었는데, 그 탓에 홈 {@code liveNow}가
 * 존재하지 않는 라이브(101·102)를 계속 "진행 중"으로 내려 카드를 누르면 시청 진입이 404가 됐다
 * 실데이터 전환으로 그 정합성 문제가 사라진다.
 *
 * <h2>섹션별 노출 정책</h2>
 *
 * <table>
 *   <tr><th>섹션</th><th>대상</th><th>정렬</th><th>최대</th></tr>
 *   <tr><td>liveNow</td><td>상태가 LIVE 인 방송만</td><td>최근 시작순</td><td>10</td></tr>
 *   <tr><td>scheduledLives</td><td>SCHEDULED 이면서 예정 시각이 아직 안 지난 방송</td>
 *       <td>임박순</td><td>10</td></tr>
 *   <tr><td>onSaleProducts</td><td>ON_SALE 상품</td><td>최신 등록순</td><td>20</td></tr>
 *   <tr><td>upcomingAuctionProducts</td><td>AUCTION_SCHEDULED 상품</td><td>최신 등록순</td><td>20</td></tr>
 *   <tr><td>categorySections</td><td>대분류 6개, 각 탭의 ON_SALE 상품</td><td>최신 등록순</td><td>탭당 8</td></tr>
 * </table>
 *
 * <p><b>빈 섹션도 키는 항상 내려간다</b>(빈 배열). 키가 사라지면 FE가 매번 존재 여부를 확인해야 한다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class HomeService {

    private static final int LIVE_LIMIT = 10;
    private static final int PRODUCT_LIMIT = 20;
    private static final int CATEGORY_SECTION_LIMIT = 6;
    private static final int CATEGORY_SECTION_PRODUCT_LIMIT = 8;
    // 카테고리 마스터의 대분류 depth. 1=성별(남성/여성/공용), 2=옷 종류(아우터/상의/...) — 탭은
    // depth=2를 쓴다. 성별(depth=1)은 탭이 아니라 카테고리 트리의 루트일 뿐이다.
    private static final short CATEGORY_TAB_DEPTH = 2;

    private final LiveRepository liveRepository;
    private final HomeProductQueryRepository productQueryRepository;
    private final CategoryRepository categoryRepository;
    private final LiveCardAssembler liveCardAssembler;
    private final ProductCardAssembler productCardAssembler;

    /**
     * @param memberId 로그인 회원 ID. <b>비회원이면 null</b>이며 이때 상품 카드의 찜 여부는 null로 내린다.
     */
    public HomeContentResponse getHomeContent(Long memberId) {
        return new HomeContentResponse(
                liveNow(),
                scheduledLives(),
                onSaleProducts(memberId),
                upcomingAuctionProducts(memberId),
                categoryProductSections(memberId));
    }

    /**
     * 진행 중인 방송만. <b>종료된 방송이 섞이면 안 된다</b> — 리포지토리 질의가 상태를
     * {@code LIVE}로 고정하고 있어 호출부 실수로 다시 새어 나올 수 없다.
     */
    private List<LiveCardResponse> liveNow() {
        List<Live> lives = liveRepository.findByStatusOrderByStartedAtDesc(
                LiveStatus.LIVE, PageRequest.of(0, LIVE_LIMIT));
        return liveCardAssembler.toCards(lives);
    }

    /**
     * 예정 방송. <b>예정 시각이 이미 지난 방송은 뺀다.</b> 호스트가 시작하지 않은 방송이
     * 언제까지고 "곧 시작"으로 홈 상단에 남으면 안 된다.
     */
    private List<LiveCardResponse> scheduledLives() {
        List<Live> lives = liveRepository.findByStatusAndScheduledAtAfterOrderByScheduledAtAsc(
                LiveStatus.SCHEDULED, LocalDateTime.now(), PageRequest.of(0, LIVE_LIMIT));
        return liveCardAssembler.toCards(lives);
    }

    private List<ProductCardResponse> onSaleProducts(Long memberId) {
        return productCardAssembler.toCards(findByStatus(SaleStatus.ON_SALE, PRODUCT_LIMIT), memberId);
    }

    private List<ProductCardResponse> upcomingAuctionProducts(Long memberId) {
        return productCardAssembler.toCards(
                findByStatus(SaleStatus.AUCTION_SCHEDULED, PRODUCT_LIMIT), memberId);
    }

    private List<Product> findByStatus(SaleStatus status, int limit) {
        return productQueryRepository.findBySaleStatusOrderByCreatedAtDesc(
                status, PageRequest.of(0, limit));
    }

    /**
     * 카테고리 탭 섹션. 탭은 카테고리 마스터의 <b>옷 종류 대분류(depth=2)</b> 앞 6개다
     * (아우터·상의·하의·신발·가방·액세서리).
     *
     * <p>상품은 그 아래 소분류(depth=3)에 달리므로 탭마다 하위 카테고리 ID를 재귀적으로 펼쳐서
     * 묶는다. 탭별로 따로 질의하면 탭 수만큼 왕복하므로, <b>여섯 탭의 카테고리를 한 번에 묶어
     * 조회한 뒤 메모리에서 나눈다.</b>
     */
    private List<CategoryProductSectionResponse> categoryProductSections(Long memberId) {
        List<Category> all = categoryRepository.findAllByOrderByIdAsc();
        List<Category> roots = all.stream()
                .filter(category -> category.getDepth() == CATEGORY_TAB_DEPTH)
                .limit(CATEGORY_SECTION_LIMIT)
                .toList();
        if (roots.isEmpty()) {
            return List.of();
        }

        // parentId → 그 바로 아래 자식 카테고리들. 트리 깊이가 늘어나도 재귀로 그대로 대응한다.
        Map<Long, List<Category>> childrenByParentId = new LinkedHashMap<>();
        all.forEach(category -> childrenByParentId
                .computeIfAbsent(category.getParentId(), key -> new ArrayList<>())
                .add(category));

        // 대분류 ID → 그 대분류에 속하는 카테고리 ID들(자기 자신 + 모든 하위 소분류, 깊이 무관).
        Map<Long, List<Long>> categoryIdsByRoot = new LinkedHashMap<>();
        roots.forEach(root -> {
            List<Long> descendantIds = new ArrayList<>(List.of(root.getId()));
            collectDescendantIds(root.getId(), childrenByParentId, descendantIds);
            categoryIdsByRoot.put(root.getId(), descendantIds);
        });

        List<Long> allCategoryIds = categoryIdsByRoot.values().stream().flatMap(List::stream).toList();
        // 탭 수 × 탭당 개수보다 넉넉히 가져와야 특정 탭에 상품이 몰려도 다른 탭이 비지 않는다.
        List<Product> products = productQueryRepository.findByCategoryIdInAndSaleStatusOrderByCreatedAtDesc(
                allCategoryIds,
                SaleStatus.ON_SALE,
                PageRequest.of(0, CATEGORY_SECTION_LIMIT * CATEGORY_SECTION_PRODUCT_LIMIT * 4));

        Map<Long, Long> rootByCategoryId = new LinkedHashMap<>();
        categoryIdsByRoot.forEach((rootId, ids) -> ids.forEach(id -> rootByCategoryId.put(id, rootId)));

        return roots.stream()
                .map(root -> toSection(root, products, rootByCategoryId, memberId))
                .toList();
    }

    /** {@code parentId} 아래 모든 하위 카테고리 ID를 깊이 제한 없이 {@code out}에 누적한다. */
    private void collectDescendantIds(
            Long parentId, Map<Long, List<Category>> childrenByParentId, List<Long> out) {
        for (Category child : childrenByParentId.getOrDefault(parentId, List.of())) {
            out.add(child.getId());
            collectDescendantIds(child.getId(), childrenByParentId, out);
        }
    }

    private CategoryProductSectionResponse toSection(
            Category root, List<Product> products, Map<Long, Long> rootByCategoryId, Long memberId) {
        List<Product> sectionProducts = products.stream()
                .filter(product -> Objects.equals(rootByCategoryId.get(product.getCategoryId()), root.getId()))
                .limit(CATEGORY_SECTION_PRODUCT_LIMIT)
                .toList();

        return new CategoryProductSectionResponse(
                String.valueOf(root.getId()),
                root.getName(),
                root.getName(),
                productCardAssembler.toCards(sectionProducts, memberId));
    }
}