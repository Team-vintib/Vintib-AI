<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import HomeSection from '@/domains/home/components/HomeSection.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomeCategoryProductSection } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const props = defineProps<{
  sections: HomeCategoryProductSection[]
  wishedProductIds: Set<number>
}>()

const emit = defineEmits<{
  toggleWish: [productId: number]
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
        <template v-if="activeSection.products.length">
          <ProductCard
            v-for="product in activeSection.products"
            :key="product.id"
            :product="product"
            :to="getProductPath(product.id)"
            :badge-label="product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매'"
            :badge-variant="product.saleType === 'AUCTION' ? 'auction' : 'direct'"
            :is-wished="wishedProductIds.has(product.id)"
            @toggle-wish="emit('toggleWish', $event)"
          />
        </template>
        <p v-else class="category-products__empty">
          이 카테고리에 표시할 상품이 없습니다.
        </p>
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
  min-height: 36px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
  transition:
    border-color 200ms ease,
    background-color 200ms ease,
    color 200ms ease;
}

.category-products__tab:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

.category-products__tab--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.category-products__tab:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.category-products__panel {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

.category-products__empty {
  grid-column: 1 / -1;
  display: grid;
  min-height: 180px;
  place-items: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
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
