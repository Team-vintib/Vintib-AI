<template>
  <section
    class="product-detail-skeleton"
    aria-label="상품 상세 정보를 불러오는 중"
    aria-live="polite"
  >
    <span class="sr-only">상품 상세 정보를 불러오는 중입니다.</span>

    <div class="product-detail-skeleton__hero">
      <div class="product-detail-skeleton__gallery">
        <div class="product-detail-skeleton__thumbnails">
          <span v-for="index in 4" :key="index" />
        </div>
        <div class="product-detail-skeleton__image" />
      </div>

      <div class="product-detail-skeleton__summary">
        <span class="product-detail-skeleton__line product-detail-skeleton__line--short" />
        <span class="product-detail-skeleton__line product-detail-skeleton__line--title" />
        <span class="product-detail-skeleton__line product-detail-skeleton__line--price" />
        <div class="product-detail-skeleton__seller" />
        <div class="product-detail-skeleton__quick-info">
          <span v-for="index in 3" :key="index" />
        </div>
        <div class="product-detail-skeleton__actions">
          <span v-for="index in 3" :key="index" />
        </div>
        <div class="product-detail-skeleton__purchase" />
      </div>
    </div>

    <div class="product-detail-skeleton__section" />
    <div class="product-detail-skeleton__section product-detail-skeleton__section--large" />
  </section>
</template>

<style scoped lang="scss">
.sr-only {
  position: absolute;
  overflow: hidden;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.product-detail-skeleton {
  display: grid;
  gap: var(--space-12);
}

.product-detail-skeleton__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(390px, 0.92fr);
  gap: var(--space-12);
}

.product-detail-skeleton__gallery {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: var(--space-4);
}

.product-detail-skeleton__thumbnails {
  display: grid;
  align-content: start;
  gap: var(--space-3);
}

.product-detail-skeleton__thumbnails span,
.product-detail-skeleton__image,
.product-detail-skeleton__line,
.product-detail-skeleton__seller,
.product-detail-skeleton__quick-info span,
.product-detail-skeleton__actions span,
.product-detail-skeleton__purchase,
.product-detail-skeleton__section {
  background: linear-gradient(
    100deg,
    var(--color-surface-secondary) 30%,
    var(--color-surface) 50%,
    var(--color-surface-secondary) 70%
  );
  background-size: 220% 100%;
  animation: product-detail-skeleton-pulse 1.35s ease-in-out infinite;
}

.product-detail-skeleton__thumbnails span {
  width: 72px;
  aspect-ratio: 4 / 5;
  border-radius: var(--radius-control);
}

.product-detail-skeleton__image {
  aspect-ratio: 4 / 5;
  border-radius: var(--radius-media);
}

.product-detail-skeleton__summary {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  padding-top: var(--space-2);
}

.product-detail-skeleton__line {
  display: block;
  height: 18px;
  border-radius: var(--radius-control);
}

.product-detail-skeleton__line--short {
  width: 42%;
}

.product-detail-skeleton__line--title {
  width: 82%;
  height: 36px;
}

.product-detail-skeleton__line--price {
  width: 45%;
  height: 40px;
}

.product-detail-skeleton__seller {
  height: 78px;
  margin-top: var(--space-4);
  border-radius: var(--radius-control);
}

.product-detail-skeleton__quick-info,
.product-detail-skeleton__actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.product-detail-skeleton__quick-info span {
  height: 78px;
  border-radius: var(--radius-control);
}

.product-detail-skeleton__actions span {
  height: var(--button-height-compact);
  border-radius: var(--radius-control);
}

.product-detail-skeleton__purchase {
  height: var(--button-height-major);
  border-radius: var(--radius-control);
}

.product-detail-skeleton__section {
  height: 150px;
  border-radius: var(--radius-card);
}

.product-detail-skeleton__section--large {
  height: 360px;
}

@keyframes product-detail-skeleton-pulse {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -120% 0;
  }
}

@media (max-width: 940px) {
  .product-detail-skeleton__hero {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .product-detail-skeleton * {
    animation: none;
  }
}
</style>
