<script setup lang="ts">
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

defineProps<{
  product: ProductDetailViewData
}>()
</script>

<template>
  <section class="detail-information" aria-labelledby="detail-information-title">
    <h2 id="detail-information-title">상품 상세 정보</h2>

    <p class="detail-information__description">{{ product.description }}</p>

    <dl class="detail-information__specs">
      <div>
        <dt>표기 사이즈</dt>
        <dd>{{ product.sizeLabel }}</dd>
      </div>
      <div>
        <dt>색상</dt>
        <dd>{{ product.color }}</dd>
      </div>
      <div>
        <dt>소재</dt>
        <dd>{{ product.material }}</dd>
      </div>
      <div>
        <dt>생산 시기</dt>
        <dd>1990년대</dd>
      </div>
      <div>
        <dt>생산 국가</dt>
        <dd>대한민국</dd>
      </div>
      <div>
        <dt>상품 상태</dt>
        <dd>{{ product.conditionLabel }}</dd>
      </div>
    </dl>

    <div class="detail-information__sizes">
      <h3>실측</h3>
      <dl>
        <div>
          <dt>어깨</dt>
          <dd>48cm</dd>
        </div>
        <div>
          <dt>가슴</dt>
          <dd>56cm</dd>
        </div>
        <div>
          <dt>소매</dt>
          <dd>61cm</dd>
        </div>
        <div>
          <dt>총장</dt>
          <dd>67cm</dd>
        </div>
      </dl>
    </div>

    <aside class="detail-information__seller-note" aria-label="판매자 고지">
      <strong>판매자 고지</strong>
      <p>
        판매자가 직접 입력한 상품 정보입니다. 아래 AI 분석 결과와 구분해서 확인해 주세요.
      </p>
    </aside>
  </section>
</template>

<style scoped lang="scss">
.detail-information {
  margin-top: var(--space-12);
}

.detail-information > h2 {
  color: var(--color-text-primary);
  font-size: 26px;
  font-weight: 700;
  line-height: 36px;
}

.detail-information__description {
  margin-top: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 400;
  line-height: 24px;
}

.detail-information__specs {
  display: grid;
  grid-template-columns: 1fr;
  margin-top: var(--space-4);
  border: 1px solid var(--color-border);
  border-bottom: 0;
  border-radius: var(--radius-card);
  overflow: hidden;
}

.detail-information__specs div {
  display: grid;
  grid-template-columns: 180px 1fr;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.detail-information__specs dt {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

.detail-information__specs dd {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 24px;
}

.detail-information__sizes {
  margin-top: var(--space-8);
}

.detail-information__sizes h3 {
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.detail-information__sizes dl {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  border-left: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
}

.detail-information__sizes div {
  padding: var(--space-4);
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  text-align: center;
}

.detail-information__sizes dt {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

.detail-information__sizes dd {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 24px;
}

.detail-information__seller-note {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-8);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.detail-information__seller-note strong {
  flex: 0 0 auto;
  font-size: 15px;
  font-weight: 600;
  line-height: 24px;
}

.detail-information__seller-note p {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

@media (max-width: 720px) {
  .detail-information__sizes dl {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .detail-information__specs div {
    grid-template-columns: 112px 1fr;
  }

  .detail-information__seller-note {
    display: block;
  }

  .detail-information__seller-note p {
    margin-top: var(--space-1);
  }
}
</style>
