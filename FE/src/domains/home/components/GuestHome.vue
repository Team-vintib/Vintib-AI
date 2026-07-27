<template>
  <section class="home-shell home-shell--guest" aria-labelledby="guest-home-title">
    <p class="home-shell__eyebrow">Vintib</p>
    <h1 id="guest-home-title" class="home-shell__title">라이브로 확인하고 경매로 만나는 빈티지 쇼핑</h1>
    <p class="home-shell__description">
      로그인하시면 Vintib의 라이브, 경매, 상품 구매 등 더 다양한 기능을 즐길 수 있습니다.
    </p>
  </section>
</template>

<style scoped lang="scss">
.home-shell {
  display: grid;
  gap: var(--space-4);
  min-height: 360px;
  align-content: center;
}

.home-shell__eyebrow {
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 700;
}

.home-shell__title {
  max-width: 720px;
  color: var(--color-text-primary);
  font-size: 40px;
  font-weight: 800;
  line-height: 1.2;
}

.home-shell__description {
  max-width: 560px;
  color: var(--color-text-secondary);
  font-size: 17px;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .home-shell {
    min-height: 300px;
  }

  .home-shell__title {
    font-size: 30px;
  }

  .home-shell__description {
    font-size: 15px;
  }
}
</style>
