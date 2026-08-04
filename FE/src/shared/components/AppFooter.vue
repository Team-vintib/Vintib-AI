<script setup lang="ts">
import logoImage from '@/assets/images/logo.png'
import { ROUTE_PATHS, type RoutePath } from '@/shared/constants/routes'

interface FooterLink {
  label: string
  to?: RoutePath
}

interface FooterGroup {
  title: string
  links: FooterLink[]
}

const footerGroups: FooterGroup[] = [
  {
    title: '서비스',
    links: [
      { label: '라이브', to: ROUTE_PATHS.LIVE_LIST },
      { label: '상품', to: ROUTE_PATHS.PRODUCT_LIST },
      { label: '판매자', to: ROUTE_PATHS.FOLLOWING_HOME },
      { label: '경매', to: ROUTE_PATHS.PRODUCT_LIST },
    ],
  },
  {
    title: '고객지원',
    links: [
      { label: '공지사항' },
      { label: '이용약관' },
      { label: '개인정보처리방침' },
      { label: '고객센터' },
    ],
  },
  {
    title: '판매자',
    links: [
      { label: '판매자 센터', to: ROUTE_PATHS.BIZ_VERIFY },
      { label: '상품 등록', to: ROUTE_PATHS.PRODUCT_CREATE },
      { label: '라이브 시작', to: ROUTE_PATHS.LIVE_CREATE },
      { label: '정산', to: ROUTE_PATHS.POINT },
    ],
  },
]
</script>

<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <section class="app-footer__brand" aria-label="VinTib 팀 정보">
        <img class="app-footer__logo" :src="logoImage" alt="VinTib" />
        <p class="app-footer__description">빈티지 패션 라이브 경매 마켓플레이스</p>
        <dl class="app-footer__contact">
          <div>
            <dt>팀</dt>
            <dd>S15P11A108</dd>
          </div>
          <div>
            <dt>문의</dt>
            <dd><a href="tel:0212345678">02-1234-5678</a></dd>
          </div>
          <div>
            <dt>운영</dt>
            <dd>평일 10:00 - 18:00</dd>
          </div>
        </dl>
        <p class="app-footer__copyright">©2026 VinTib Inc. All rights reserved.</p>
      </section>

      <nav class="app-footer__nav" aria-label="하단 메뉴">
        <section v-for="group in footerGroups" :key="group.title" class="app-footer__group">
          <h2 class="app-footer__group-title">{{ group.title }}</h2>
          <ul class="app-footer__links">
            <li v-for="link in group.links" :key="link.label">
              <RouterLink v-if="link.to" class="app-footer__link" :to="link.to">
                {{ link.label }}
              </RouterLink>
              <span v-else class="app-footer__link app-footer__link--static">
                {{ link.label }}
              </span>
            </li>
          </ul>
        </section>
      </nav>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  border-top: 1px solid var(--color-border);
  background: var(--color-chrome);
}

.app-footer__inner {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) auto;
  width: 100%;
  max-width: var(--layout-content-max-width);
  min-height: 220px;
  padding: var(--space-12) var(--layout-gutter);
  margin-inline: auto;
  gap: var(--space-16);
}

.app-footer__brand {
  display: grid;
  align-content: start;
  gap: var(--space-3);
}

.app-footer__logo {
  width: 116px;
  height: 40px;
  object-fit: contain;
}

.app-footer__description,
.app-footer__copyright,
.app-footer__contact {
  color: var(--color-text-muted);
}

.app-footer__description,
.app-footer__copyright {
  font-size: 14px;
  line-height: 22px;
}

.app-footer__contact {
  display: grid;
  gap: var(--space-1);
  margin-top: var(--space-1);
  font-size: 13px;
  line-height: 20px;
}

.app-footer__contact div {
  display: flex;
  gap: var(--space-2);
}

.app-footer__contact dt {
  min-width: 32px;
  color: var(--color-text-secondary);
  font-weight: 700;
}

.app-footer__contact dd {
  color: var(--color-text-muted);
}

.app-footer__contact a:hover,
.app-footer__link:hover {
  color: var(--color-primary);
}

.app-footer__nav {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: var(--space-12);
}

.app-footer__group {
  display: grid;
  align-content: start;
  gap: var(--space-4);
}

.app-footer__group-title {
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: 800;
  line-height: 24px;
}

.app-footer__links {
  display: grid;
  gap: var(--space-2);
  list-style: none;
}

.app-footer__link {
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 600;
  line-height: 24px;
  transition: color 160ms ease;
}

.app-footer__link--static {
  cursor: default;
}

.app-footer__link:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

@media (max-width: 860px) {
  .app-footer__inner {
    grid-template-columns: 1fr;
    padding: var(--space-10) var(--space-5);
    gap: var(--space-8);
  }

  .app-footer__nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-5);
  }
}

@media (max-width: 560px) {
  .app-footer__nav {
    grid-template-columns: 1fr;
  }
}
</style>
