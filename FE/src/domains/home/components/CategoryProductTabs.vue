<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import HomeSection from '@/domains/home/components/HomeSection.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomeCategoryProductSection } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const props = defineProps<{
  sections: HomeCategoryProductSection[]
}>()

const activeSectionId = ref(props.sections[0]?.id ?? '')

watch(
  () => props.sections,
  (sections) => {
    if (!sections.some((section) => section.id === activeSectionId.value)) {
      activeSectionId.value = sections[0]?.id ?? ''
    }
  },
)

const activeSection = computed(
  () =>
    props.sections.find((section) => section.id === activeSectionId.value) ?? props.sections[0],
)

const getProductPath = (productId: number) => `/products/${productId}`
</script>

<template>
  <HomeSection
    title-id="category-product-title"
    eyebrow="Category"
    title="카테고리별 상품"
    :link-to="ROUTE_PATHS.PRODUCT_LIST"
    :is-empty="sections.length === 0"
    empty-message="표시할 카테고리 상품이 없습니다."
  >
    <div class="category-products">
      <div class="category-products__tabs" role="tablist" aria-label="카테고리별 상품">
        <button
          v-for="section in sections"
          :id="`category-product-tab-${section.id}`"
          :key="section.id"
          type="button"
          class="category-products__tab"
          :class="{ 'category-products__tab--active': activeSectionId === section.id }"
          role="tab"
          :aria-selected="activeSectionId === section.id"
          :aria-controls="`category-product-panel-${section.id}`"
          @click="activeSectionId = section.id"
        >
          {{ section.title }}
        </button>
      </div>

      <div
        v-if="activeSection"
        :id="`category-product-panel-${activeSection.id}`"
        class="category-products__panel"
        role="tabpanel"
        :aria-labelledby="`category-product-tab-${activeSection.id}`"
      >
        <ProductCard
          v-for="product in activeSection.products"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          :badge-label="product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매'"
          :badge-variant="product.saleType === 'AUCTION' ? 'auction' : 'direct'"
        />
      </div>
    </div>
  </HomeSection>
</template>

<style scoped lang="scss">
.category-products {
  display: grid;
  gap: var(--space-5);
}

.category-products__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.category-products__tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-chip);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
  white-space: nowrap;
}

.category-products__tab:hover,
.category-products__tab:focus-visible,
.category-products__tab--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.category-products__tab:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.category-products__panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

@media (max-width: 768px) {
  .category-products__panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .category-products__tab {
    min-height: 34px;
    padding: 0 var(--space-3);
    font-size: 13px;
  }

  .category-products__panel {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }
}
</style>
