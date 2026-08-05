<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { SearchMemberResult } from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

defineProps<{
  member: SearchMemberResult
}>()

// 아바타 로드에 실패하면 대체 이미지를 새로 추가하는 대신 빈 원형 프레임만 남긴다(홈 화면과 동일).
const handleAvatarError = (event: Event) => {
  if (event.target instanceof HTMLImageElement) {
    event.target.style.visibility = 'hidden'
  }
}
</script>

<template>
  <RouterLink
    class="search-member-card"
    :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: member.id } }"
    :aria-label="`${member.nickname} 프로필 보기`"
  >
    <span class="search-member-card__avatar">
      <img
        v-if="member.profileImageUrl"
        :src="member.profileImageUrl"
        :alt="member.nickname"
        @error="handleAvatarError"
      />
    </span>
    <span class="search-member-card__body">
      <strong class="search-member-card__name">{{ member.nickname }}</strong>
      <span class="search-member-card__stats">
        <span>팔로워 {{ member.followerCount.toLocaleString('ko-KR') }}</span>
        <span>판매 상품 {{ member.productCount.toLocaleString('ko-KR') }}</span>
      </span>
    </span>
  </RouterLink>
</template>

<style scoped lang="scss">
// 홈 화면 "팔로우 중인 판매자" 카드(seller-card)와 같은 형태 — 얇은 border만, hover도 뜨지 않고
// 보더 대비만 미세하게 바뀐다. 아바타는 왼쪽, 닉네임·통계는 오른쪽에 배치한다.
.search-member-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
  text-decoration: none;
  transition: border-color var(--transition-standard);
}

.search-member-card:hover {
  border-color: var(--color-border-strong);
}

.search-member-card:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 3px;
}

.search-member-card__avatar {
  overflow: hidden;
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: var(--space-16);
  height: var(--space-16);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-image-frame);
}

.search-member-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
}

.search-member-card__body {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.search-member-card__name {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-comfortable);
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-member-card:hover .search-member-card__name,
.search-member-card:focus-visible .search-member-card__name {
  color: var(--color-primary);
}

.search-member-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: -0.01em;
  line-height: var(--line-height-snug);
  font-variant-numeric: tabular-nums;
}
</style>
