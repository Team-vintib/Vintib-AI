package com.ssafy.backend.live.port;

import com.ssafy.backend.global.config.S3Config.AwsProperties;
import com.ssafy.backend.global.storage.S3StorageService;
import com.ssafy.backend.product.entity.Brand;
import com.ssafy.backend.product.entity.Category;
import com.ssafy.backend.product.entity.Product;
import com.ssafy.backend.product.repository.BrandRepository;
import com.ssafy.backend.product.repository.CategoryRepository;
import com.ssafy.backend.product.repository.ProductRepository;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/**
 * {@link ProductQueryPort}의 실제 구현. 상품 도메인의 리포지토리에 위임한다.
 *
 * <p>계획(JY005) 초안에서는 상품 도메인이 없어 스텁으로 두려 했으나, 상품 등록·조회(-238 등)가
 * 이미 들어와 있어 처음부터 실제 조회로 붙인다. 상품 도메인 코드는 읽기만 하고 수정하지 않는다.
 */
@Component
@RequiredArgsConstructor
public class ProductQueryAdapter implements ProductQueryPort {

    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;
    private final BrandRepository brandRepository;
    private final ProductImageQueryRepository productImageQueryRepository;
    private final S3StorageService s3StorageService;
    private final AwsProperties awsProperties;

    @Override
    public Map<Long, ProductCard> findCards(Collection<Long> productIds) {
        if (productIds.isEmpty()) {
            return Map.of();
        }

        List<Product> products = productRepository.findAllById(productIds);
        if (products.isEmpty()) {
            return Map.of();
        }

        Map<Long, String> brandNameById = brandNames(products);
        Map<Long, String> thumbnailByProductId = thumbnails(products);

        return products.stream().collect(Collectors.toMap(
                Product::getId,
                product -> new ProductCard(
                        product.getId(),
                        product.getTitle(),
                        product.getBrandId() == null ? null : brandNameById.get(product.getBrandId()),
                        product.getPrice(),
                        product.getSaleType() == null ? null : product.getSaleType().name(),
                        product.getConditionGrade(),
                        thumbnailByProductId.get(product.getId()))));
    }

    private Map<Long, String> brandNames(List<Product> products) {
        List<Long> brandIds = products.stream()
                .map(Product::getBrandId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (brandIds.isEmpty()) {
            return Map.of();
        }
        return brandRepository.findAllById(brandIds).stream()
                .collect(Collectors.toMap(Brand::getId, Brand::getName));
    }

    /**
     * 상품별 대표 이미지 URL. 쿼리가 {@code primary DESC, sortOrder ASC} 로 정렬해 오므로
     * <b>상품마다 첫 행이 대표</b>다. 그래서 병합 함수에서 먼저 온 것을 남긴다.
     */
    private Map<Long, String> thumbnails(List<Product> products) {
        String bucket = awsProperties.s3().publicBucket();
        return productImageQueryRepository
                .findAllByProductIds(products.stream().map(Product::getId).toList()).stream()
                .collect(Collectors.toMap(
                        image -> image.getProduct().getId(),
                        image -> s3StorageService.publicUrl(bucket, image.getImageKey()),
                        (first, later) -> first));
    }

    @Override
    public Optional<ProductSummary> findById(Long productId) {
        return productRepository.findById(productId)
                .map(product -> new ProductSummary(
                        product.getId(), product.getSeller().getId(), product.getTitle()));
    }

    @Override
    public List<CategorySummary> findRootCategories(Collection<Long> productIds) {
        return findRootCategoryByProductId(productIds).values().stream()
                .distinct()
                .sorted(Comparator.comparing(CategorySummary::id))
                .toList();
    }

    @Override
    public Map<Long, CategorySummary> findRootCategoryByProductId(Collection<Long> productIds) {
        if (productIds.isEmpty()) {
            return Map.of();
        }

        List<Product> products = productRepository.findAllById(productIds);
        if (products.isEmpty()) {
            return Map.of();
        }

        // 소분류는 부모(대분류)로 올린다. 최상위는 parentId 가 없으므로 자기 자신이 대분류다.
        Map<Long, Long> rootIdByCategoryId = categoryRepository
                .findAllById(products.stream().map(Product::getCategoryId).distinct().toList()).stream()
                .collect(Collectors.toMap(
                        Category::getId,
                        category -> category.getParentId() == null ? category.getId() : category.getParentId()));

        Map<Long, CategorySummary> rootById = categoryRepository
                .findAllById(Set.copyOf(rootIdByCategoryId.values())).stream()
                .collect(Collectors.toMap(
                        Category::getId, category -> new CategorySummary(category.getId(), category.getName())));

        return products.stream()
                .filter(product -> rootIdByCategoryId.containsKey(product.getCategoryId()))
                .collect(Collectors.toMap(
                        Product::getId,
                        product -> rootById.get(rootIdByCategoryId.get(product.getCategoryId())),
                        (a, b) -> a));
    }

    @Override
    public List<Long> findProductIdsInCategories(Collection<Long> categoryIds) {
        if (categoryIds.isEmpty()) {
            return List.of();
        }

        // 대분류를 고르면 하위 소분류 상품까지 잡아야 한다. 요청에 소분류가 섞여 있어도
        // 그 소분류는 자식이 없으므로 확장 결과가 자기 자신뿐이라 그대로 동작한다.
        Set<Long> expanded = new LinkedHashSet<>(categoryIds);
        categoryRepository.findByParentIdIn(categoryIds).forEach(child -> expanded.add(child.getId()));

        return productRepository.findByCategoryIdIn(expanded).stream()
                .map(Product::getId)
                .toList();
    }
}