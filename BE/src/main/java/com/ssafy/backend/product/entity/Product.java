package com.ssafy.backend.product.entity;

import com.ssafy.backend.global.entity.BaseTimeEntity;
import com.ssafy.backend.member.entity.Member;
import jakarta.persistence.CheckConstraint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import java.util.Map;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.SQLRestriction;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
        name = "product",
        check = {
                @CheckConstraint(
                        name = "ck_product_sale_type",
                        constraint = "sale_type IN ('DIRECT_SALE', 'AUCTION')"),
                @CheckConstraint(
                        name = "ck_product_sale_status",
                        constraint = "sale_status IN ("
                                + "'DRAFT', 'ON_SALE', 'AUCTION_SCHEDULED', 'AUCTION_IN_PROGRESS', 'SOLD')"),
                @CheckConstraint(
                        name = "ck_product_price_by_type",
                        constraint = "sale_type <> 'DIRECT_SALE' OR price IS NOT NULL"),
                @CheckConstraint(
                        name = "ck_product_ai_model_gender",
                        constraint = "ai_model_enabled = false OR ai_model_gender IS NOT NULL")
        })
@SQLRestriction("deleted_at IS NULL")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "seller_id", nullable = false)
    private Member seller;

    // 카테고리는 필수다. 미분류 상품은 검색·필터에서 누락되고, 라이브 카테고리(편성 상품에서
    // 유도)도 만들 수 없다.
    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    // FE가 브랜드 마스터에서 고르게 하지 않고 자유 텍스트로 받는다(브랜드 FK 제거) — 미등록
    // 브랜드·오탈자·병기 표기까지 그대로 받아야 해서 브랜드 마스터로는 표현할 수 없다.
    @Column(name = "brand", length = 100)
    private String brand;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    // 중고 상태 등급 체계 미확정 — 자유 문자열 (docs/db/erd.md 확인 필요 가정 #3)
    @Column(name = "condition_grade", length = 20)
    private String conditionGrade;

    // AI 품질 검수가 매긴 원점수(0~100, SY043). 041-quality-inspection-integration.md 경고 그대로:
    // 가중치·등급 경계가 근거 없는 임의값이라 가격책정 등 다른 로직이 이 값을 신뢰해 쓰면 안 된다
    // — 상품 상세에 참고용으로 보여주는 것 외 용도로 참조하지 않는다.
    @Column(name = "condition_score")
    private Double conditionScore;

    @Column(name = "size_label", length = 50)
    private String sizeLabel;

    @Column(length = 50)
    private String color;

    @Column(length = 50)
    private String material;

    // "동일 상품" 판정 키(AI 시세 조회, CH030). 상품명+브랜드+카테고리 텍스트로 AI가 계산해
    // 돌려준 값을 FE가 폴링해서 그대로 넘겨준다 — BE는 저장·조회만 한다(직접 계산 안 함).
    // 같은 값을 가진 상품끼리 GET /api/products/{id}/market-price에서 "동일 상품"으로 묶인다.
    @Column(name = "match_key", length = 300)
    private String matchKey;

    // 치수 항목(총장/어깨너비/가슴단면/소매길이 등)이 상품마다 달라 고정 컬럼 대신 JSONB로 담는다.
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Integer> measurements;

    // 판매 채널(정찰제/경매)은 이번 단계에서 정하지 않는다 — 판매 가격 설정 또는
    // 경매 조건 설정 API를 호출하는 시점에 비로소 결정된다.
    @Enumerated(EnumType.STRING)
    @Column(name = "sale_type", length = 20)
    private SaleType saleType;

    @Enumerated(EnumType.STRING)
    @Column(name = "sale_status", nullable = false, length = 30)
    private SaleStatus saleStatus;

    private Long price;

    // 마네킹 사진 기반 AI 착용컷 사용 여부. true면 aiModelGender가 반드시 있어야 한다
    // (ck_product_ai_model_gender). 프로필 표시용이 아니라 "합성 시 어떤 성별 모델 사진을 쓸지"를
    // 판매자가 정하는 값이다.
    @ColumnDefault("false")
    @Column(name = "ai_model_enabled", nullable = false)
    private boolean aiModelEnabled;

    @Enumerated(EnumType.STRING)
    @Column(name = "ai_model_gender", length = 10)
    private AiModelGender aiModelGender;

    // AI 착용컷 생성 job 상태. 대표 이미지가 등록되는 시점(ProductImageService.registerImage)에
    // PENDING으로 시작한다 — 등록 직후엔 아직 job이 없어 NONE이다.
    @Enumerated(EnumType.STRING)
    @ColumnDefault("'NONE'")
    @Column(name = "ai_model_cut_status", nullable = false, length = 10)
    private AiModelCutStatus aiModelCutStatus = AiModelCutStatus.NONE;

    @Column(name = "ai_model_cut_job_id", length = 100)
    private String aiModelCutJobId;

    // AI 게이트웨이가 돌려준 결과 이미지 URL을 그대로 저장한다 — BE S3 버킷의 key가 아니라
    // AI 쪽 /results/* 정적 서빙 URL이라 S3StorageService로 다시 변환할 대상이 없다.
    @Column(name = "ai_model_cut_image_url", length = 500)
    private String aiModelCutImageUrl;

    // 하자 검수(SAM3) job 상태. 앞/뒤 이미지가 둘 다 등록되는 시점(ProductImageService.
    // registerImage)에 PENDING으로 시작한다 — ai_model_cut과 같은 이유로 등록 직후엔 NONE.
    @Enumerated(EnumType.STRING)
    @ColumnDefault("'NONE'")
    @Column(name = "quality_inspection_status", nullable = false, length = 10)
    private QualityInspectionStatus qualityInspectionStatus = QualityInspectionStatus.NONE;

    @Column(name = "quality_inspection_job_id", length = 100)
    private String qualityInspectionJobId;

    // AI 검수 결과(condition_score/findings 등) 원본을 그대로 저장한다. AI 쪽 job 결과는 Redis
    // TTL 1시간 뒤 사라지므로, 완료 시점에 여기 캐시해두지 않으면 그 이후 조회에서 영영 잃는다.
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "quality_inspection_result", columnDefinition = "jsonb")
    private Map<String, Object> qualityInspectionResult;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @Builder
    private Product(
            Member seller,
            Long categoryId,
            String brand,
            String title,
            String description,
            String conditionGrade,
            Double conditionScore,
            String sizeLabel,
            String color,
            String material,
            Map<String, Integer> measurements,
            boolean aiModelEnabled,
            AiModelGender aiModelGender) {
        this.seller = seller;
        this.categoryId = categoryId;
        this.brand = brand;
        this.title = title;
        this.description = description;
        this.conditionGrade = conditionGrade;
        this.conditionScore = conditionScore;
        this.sizeLabel = sizeLabel;
        this.color = color;
        this.material = material;
        this.measurements = measurements;
        this.aiModelEnabled = aiModelEnabled;
        this.aiModelGender = aiModelGender;
        this.saleStatus = SaleStatus.DRAFT;
    }

    public void registerDirectSale(Long price) {
        this.saleType = SaleType.DIRECT_SALE;
        this.price = price;
        this.saleStatus = SaleStatus.ON_SALE;
    }

    public void scheduleAuction() {
        this.saleType = SaleType.AUCTION;
        this.price = null;
        this.saleStatus = SaleStatus.AUCTION_SCHEDULED;
    }

    /** 이미 정찰제로 전환된 상품의 가격을 조정한다. 호출 전 {@link #isDirectSale()}을 확인해야 한다 —
     * 경매 상품은 가격 개념이 없다({@code price}는 항상 null, 시작가는 {@code Auction}이 따로 갖는다). */
    public void updatePrice(Long price) {
        this.price = price;
    }

    public boolean isDirectSale() {
        return saleType == SaleType.DIRECT_SALE;
    }

    public void update(
            String title,
            String description,
            Long categoryId,
            String brand,
            String conditionGrade,
            String sizeLabel,
            String color,
            String material,
            Map<String, Integer> measurements,
            String matchKey) {
        if (title != null) {
            this.title = title;
        }
        if (description != null) {
            this.description = description;
        }
        if (categoryId != null) {
            this.categoryId = categoryId;
        }
        if (brand != null) {
            this.brand = brand;
        }
        if (conditionGrade != null) {
            this.conditionGrade = conditionGrade;
        }
        if (sizeLabel != null) {
            this.sizeLabel = sizeLabel;
        }
        if (color != null) {
            this.color = color;
        }
        if (material != null) {
            this.material = material;
        }
        if (measurements != null) {
            this.measurements = measurements;
        }
        if (matchKey != null) {
            this.matchKey = matchKey;
        }
    }

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }

    /** 대표 이미지 등록 직후, AI 착용컷 job을 접수했을 때 호출한다. */
    public void startAiModelCutJob(String jobId) {
        this.aiModelCutJobId = jobId;
        this.aiModelCutStatus = AiModelCutStatus.PENDING;
    }

    public void completeAiModelCutJob(String imageUrl) {
        this.aiModelCutImageUrl = imageUrl;
        this.aiModelCutStatus = AiModelCutStatus.COMPLETED;
    }

    public void failAiModelCutJob() {
        this.aiModelCutStatus = AiModelCutStatus.FAILED;
    }

    public void markAiModelCutProcessing() {
        this.aiModelCutStatus = AiModelCutStatus.PROCESSING;
    }

    /** 앞/뒤 이미지가 둘 다 등록된 직후, 하자 검수 job을 접수했을 때 호출한다. */
    public void startQualityInspectionJob(String jobId) {
        this.qualityInspectionJobId = jobId;
        this.qualityInspectionStatus = QualityInspectionStatus.PENDING;
    }

    public void completeQualityInspectionJob(Map<String, Object> result) {
        this.qualityInspectionResult = result;
        this.qualityInspectionStatus = QualityInspectionStatus.COMPLETED;
    }

    public void failQualityInspectionJob() {
        this.qualityInspectionStatus = QualityInspectionStatus.FAILED;
    }

    public void markQualityInspectionProcessing() {
        this.qualityInspectionStatus = QualityInspectionStatus.PROCESSING;
    }

    /** 정찰제 즉시구매 대상인지 확인한다(SALE-002). 경매 상품이나 품절 상품은 구매할 수 없다. */
    public boolean isAvailableForDirectPurchase() {
        return saleType == SaleType.DIRECT_SALE && saleStatus == SaleStatus.ON_SALE;
    }

    /** 즉시구매 완료 처리(SALE-002). 재고가 1개뿐인 중고 상품이라 판매 완료로 바로 넘어간다. */
    public void markSold() {
        this.saleStatus = SaleStatus.SOLD;
    }

    public boolean isOwnedBy(Long memberId) {
        return memberId != null && seller.getId().equals(memberId);
    }

    public boolean isDraft() {
        return saleStatus == SaleStatus.DRAFT;
    }

    public boolean isDeleted() {
        return deletedAt != null;
    }

    /**
     * 상품 내용(제목·설명·사진 등)을 고칠 수 있는 상태인지.
     *
     * <p><b>{@code AUCTION_SCHEDULED}를 허용한다</b>(FE 요청 007) — 유찰된 상품은 이 상태로
     * 돌아오는데, 판매자 입장에서 "안 팔렸으니 설명을 고쳐 다시 걸자"가 자연스러운 흐름이다.
     * 막아 두면 정찰제로 전환했다가 되돌리는 우회로를 강요하게 된다.
     *
     * <p><b>{@code AUCTION_IN_PROGRESS}는 계속 막는다.</b> 입찰이 붙는 도중에 상품 정보가 바뀌면
     * 입찰자가 보고 판단한 것과 실제로 받는 물건이 달라진다. {@code SOLD}도 마찬가지로 막힌다.
     */
    public boolean isEditable() {
        return saleStatus == SaleStatus.DRAFT
                || saleStatus == SaleStatus.ON_SALE
                || saleStatus == SaleStatus.AUCTION_SCHEDULED;
    }
}