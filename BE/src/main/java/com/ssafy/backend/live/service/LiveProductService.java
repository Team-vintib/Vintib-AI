package com.ssafy.backend.live.service;

import com.ssafy.backend.global.exception.CustomException;
import com.ssafy.backend.global.exception.ErrorCode;
import com.ssafy.backend.live.dto.request.LiveProductLinkRequest;
import com.ssafy.backend.live.dto.response.LiveProductResponse;
import com.ssafy.backend.live.entity.Live;
import com.ssafy.backend.live.entity.LiveProduct;
import com.ssafy.backend.live.port.ProductQueryPort;
import com.ssafy.backend.live.port.ProductQueryPort.CategorySummary;
import com.ssafy.backend.live.port.ProductQueryPort.ProductSummary;
import com.ssafy.backend.live.repository.LiveProductRepository;
import com.ssafy.backend.live.repository.LiveRepository;
import java.time.LocalDateTime;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 라이브 상품 편성(LIVE-003).
 *
 * <p>{@link LiveService}와 분리한 이유는 관심사가 다르기 때문이다 — 이쪽은 방 자체가 아니라
 * 방에 걸리는 상품 목록을 다룬다. 상품 조회는 {@link ProductQueryPort}만 거친다.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class LiveProductService {

    private final LiveRepository liveRepository;
    private final LiveProductRepository liveProductRepository;
    private final ProductQueryPort productQueryPort;

    /**
     * 라이브 개설과 동시에 판매 상품을 편성한다.
     *
     * <p>개설 트랜잭션 안에서 호출되므로 라이브 조회·호스트 검증을 다시 하지 않는다. 대신
     * 상품 소유·중복 검증은 그대로 건다. 편성 순서는 요청에 담긴 순서를 그대로 쓴다.
     */
    @Transactional
    public void linkProductsOnCreate(Long hostId, Live live, List<Long> productIds) {
        // 같은 상품을 두 번 담아 보내면 부분 UNIQUE 인덱스(ux_live_product_active)에 걸려
        // 500 으로 새어 나간다. 저장 전에 걸러 400 으로 돌려준다.
        if (Set.copyOf(productIds).size() != productIds.size()) {
            throw new CustomException(ErrorCode.PRODUCT_ALREADY_LINKED);
        }

        LocalDateTime now = LocalDateTime.now();
        short sortOrder = 0;

        for (Long productId : productIds) {
            ProductSummary product = findProduct(productId);
            if (!product.sellerId().equals(hostId)) {
                throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
            }
            liveProductRepository.save(LiveProduct.link(live, product.id(), sortOrder++, now));
        }
    }

    /**
     * 라이브에 상품을 연결한다. <b>방송 시작 전(SCHEDULED)에만 가능하다</b> — 방송 도중에는
     * 편성을 바꿀 수 없다(운영 정책).
     *
     * <p>호스트 본인의 상품만 걸 수 있다 — 남의 상품을 자기 방송에 올리는 것을 막는다.
     */
    @Transactional
    public LiveProductResponse linkProduct(Long hostId, Long liveId, LiveProductLinkRequest request) {
        Live live = findEditableLive(hostId, liveId);
        ProductSummary product = findProduct(request.productId());

        if (!product.sellerId().equals(hostId)) {
            throw new CustomException(ErrorCode.NOT_PRODUCT_OWNER);
        }
        if (liveProductRepository.existsByLiveIdAndProductIdAndRemovedAtIsNull(liveId, product.id())) {
            throw new CustomException(ErrorCode.PRODUCT_ALREADY_LINKED);
        }

        LiveProduct linked = liveProductRepository.save(
                LiveProduct.link(live, product.id(), request.sortOrderOrDefault(), LocalDateTime.now()));

        return LiveProductResponse.of(linked, product.title());
    }

    /**
     * 연결을 해제한다. 물리 삭제가 아니라 제외 시각을 남긴다 — 다시보기 타임라인(LIVE-008)의 근거가 된다.
     */
    @Transactional
    public void unlinkProduct(Long hostId, Long liveId, Long productId) {
        findEditableLive(hostId, liveId);

        LiveProduct linked = liveProductRepository
                .findByLiveIdAndProductIdAndRemovedAtIsNull(liveId, productId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_PRODUCT_NOT_FOUND));

        linked.unlink(LocalDateTime.now());
    }

    /**
     * 라이브의 카테고리. <b>편성 상품에서 유도한다</b> — {@code live} 테이블에는 카테고리 컬럼이 없다.
     *
     * <p>같은 사실을 두 군데 저장하면 반드시 어긋나므로, 편성 상품을 진실로 두고 카테고리는
     * 그때그때 파생시킨다. 여러 카테고리 상품을 걸면 카테고리도 여러 개가 된다 — 대표 하나를
     * 뽑지 않는 이유는, 아우터·하의·액세서리를 파는 방송이 세 탭 모두에서 검색돼야 하기 때문이다.
     */
    public List<CategorySummary> getLiveCategories(Long liveId) {
        List<Long> productIds = liveProductRepository
                .findByLiveIdAndRemovedAtIsNullOrderBySortOrderAsc(liveId).stream()
                .map(LiveProduct::getProductId)
                .toList();

        return productQueryPort.findRootCategories(productIds);
    }

    /**
     * 라이브 여러 건의 카테고리를 한 번에 구한다. 목록 화면용 — 라이브마다
     * {@link #getLiveCategories}를 부르면 N+1이 된다.
     */
    public List<Long> findProductIdsInCategories(Collection<Long> categoryIds) {
        return productQueryPort.findProductIdsInCategories(categoryIds);
    }

    public Map<Long, List<CategorySummary>> getCategoriesByLiveIds(Collection<Long> liveIds) {
        if (liveIds.isEmpty()) {
            return Map.of();
        }

        List<LiveProduct> linked = liveProductRepository.findByLiveIdInAndRemovedAtIsNull(liveIds);
        Map<Long, CategorySummary> categoryByProductId = productQueryPort.findRootCategoryByProductId(
                linked.stream().map(LiveProduct::getProductId).distinct().toList());

        return linked.stream()
                .filter(liveProduct -> categoryByProductId.containsKey(liveProduct.getProductId()))
                .collect(Collectors.groupingBy(
                        liveProduct -> liveProduct.getLive().getId(),
                        Collectors.collectingAndThen(
                                Collectors.toList(),
                                items -> items.stream()
                                        .map(item -> categoryByProductId.get(item.getProductId()))
                                        .distinct()
                                        .sorted(Comparator.comparing(CategorySummary::id))
                                        .toList())));
    }

    /** 현재 연결 중인 상품 목록. 제외된 건은 빠진다. */
    public List<LiveProductResponse> getLinkedProducts(Long liveId) {
        if (!liveRepository.existsById(liveId)) {
            throw new CustomException(ErrorCode.LIVE_NOT_FOUND);
        }

        return liveProductRepository.findByLiveIdAndRemovedAtIsNullOrderBySortOrderAsc(liveId).stream()
                .map(liveProduct -> LiveProductResponse.of(liveProduct, productTitleOf(liveProduct.getProductId())))
                .toList();
    }

    private Live findEditableLive(Long hostId, Long liveId) {
        Live live = liveRepository.findById(liveId)
                .orElseThrow(() -> new CustomException(ErrorCode.LIVE_NOT_FOUND));

        if (!live.isHostedBy(hostId)) {
            throw new CustomException(ErrorCode.NOT_LIVE_HOST);
        }
        if (!live.isOpenForEditing()) {
            throw new CustomException(ErrorCode.INVALID_LIVE_STATE);
        }

        return live;
    }

    private ProductSummary findProduct(Long productId) {
        return productQueryPort.findById(productId)
                .orElseThrow(() -> new CustomException(ErrorCode.PRODUCT_NOT_FOUND));
    }

    // 연결 당시 존재하던 상품이 이후 삭제될 수 있다. 목록 조회가 통째로 실패하지 않도록 제목만 비운다.
    private String productTitleOf(Long productId) {
        return productQueryPort.findById(productId).map(ProductSummary::title).orElse(null);
    }
}