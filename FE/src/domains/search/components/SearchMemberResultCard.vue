<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { SearchMemberResult } from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

defineProps<{
  member: SearchMemberResult
}>()
</script>

<template>
  <RouterLink
    class="search-member-card"
    :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: member.id } }"
    :aria-label="`${member.nickname} 프로필 보기`"
  >
    <span class="search-member-card__body">
      <strong class="search-member-card__name">{{ member.nickname }}</strong>
      <span class="search-member-card__stats">
        상품 {{ member.productCount.toLocaleString('ko-KR') }} · 팔로워
        {{ member.followerCount.toLocaleString('ko-KR') }}
      </span>
    </span>
    <span class="search-member-card__arrow" aria-hidden="true">›</span>
  </RouterLink>
</template>

<style scoped lang="scss">
.search-member-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-height: 68px;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  color: inherit;
  text-decoration: none;
}

.search-member-card__body {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.search-member-card__name {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: 800;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-member-card__stats {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

.search-member-card__arrow {
  color: var(--color-text-muted);
  font-size: 24px;
  line-height: 1;
}

.search-member-card:hover .search-member-card__name,
.search-member-card:focus-visible .search-member-card__name {
  color: var(--color-primary);
  text-decoration: underline;
}

.search-member-card:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 3px;
}
</style>
