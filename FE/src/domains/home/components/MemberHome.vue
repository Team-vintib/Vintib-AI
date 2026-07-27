<template>
  <section class="home-shell home-shell--member" aria-labelledby="member-home-title">
    <p class="home-shell__eyebrow">For you</p>
    <h1 id="member-home-title" class="home-shell__title">지금 참여할 수 있는 라이브와 경매를 확인하세요</h1>
    <p class="home-shell__description">
      Vintib입니다.
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
  color: var(--color-live);
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
