<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { ROUTE_PATHS } from '@/shared/constants/routes'

const searchKeyword = ref('')
const popularKeywords = ['리바이스', '가죽 자켓', '라이브 경매', 'Archive Room']
const router = useRouter()

const getSearchTo = (keyword: string) => ({
  path: ROUTE_PATHS.SEARCH,
  query: { keyword },
})

const submitSearch = async () => {
  const keyword = searchKeyword.value.trim()

  if (!keyword) {
    await router.push(ROUTE_PATHS.SEARCH)
    return
  }

  await router.push(getSearchTo(keyword))
}
</script>

<template>
  <section class="home-search-panel" aria-label="홈 검색">
    <form class="home-search" role="search" @submit.prevent="submitSearch">
      <span class="home-search__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="m20 20-4.2-4.2m2.2-5.3a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
      <input
        v-model="searchKeyword"
        class="home-search__input"
        type="search"
        placeholder="예: 리바이스 데님 자켓, Archive Room"
      />
      <button class="home-search__button" type="submit" aria-label="검색">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
          <path
            d="m20 20-4.2-4.2m2.2-5.3a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </form>
    <div class="home-search-tags" aria-label="인기 검색어">
      <span class="home-search-tags__label">인기 검색어</span>
      <RouterLink
        v-for="keyword in popularKeywords"
        :key="keyword"
        class="home-search-tags__item"
        :to="getSearchTo(keyword)"
      >
        {{ keyword }}
      </RouterLink>
    </div>
  </section>
</template>

<style scoped lang="scss">
.home-search-panel {
  display: grid;
  width: 100%;
  place-items: center;
  gap: var(--space-2);
  padding-top: var(--space-3);
}

.home-search {
  display: flex;
  align-items: center;
  width: min(100%, 860px);
  height: 46px;
  padding: 3px 3px 3px var(--space-4);
  border: 1px solid var(--color-search-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.home-search:focus-within {
  border-color: var(--color-search-button);
  box-shadow: 0 0 0 4px rgba(47, 75, 58, 0.08);
}

.home-search__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--color-search-icon);
}

.home-search__icon svg {
  width: 18px;
  height: 18px;
}

.home-search__input {
  height: 38px;
  min-width: 0;
  border: 0;
  flex: 1;
  padding: 0 var(--space-3);
  background: transparent;
  color: var(--color-text-primary);
  font-size: 15px;
  line-height: 38px;
  outline: none;
}

.home-search__input::placeholder {
  color: var(--color-text-muted);
}

.home-search__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: var(--color-search-button);
  color: var(--color-text-inverse);
  font-weight: 700;
  line-height: 20px;
  white-space: nowrap;
}

.home-search__button svg {
  width: 18px;
  height: 18px;
}

.home-search__button:hover {
  background: var(--color-search-button-hover);
}

.home-search-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  width: min(100%, 860px);
}

.home-search-tags__label {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 20px;
}

.home-search-tags__item {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-chip);
  background: rgba(255, 255, 255, 0.62);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.home-search-tags__item:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

@media (max-width: 520px) {
  .home-search {
    display: flex;
    gap: var(--space-1);
    padding: var(--space-2);
    height: 52px;
  }

  .home-search__icon {
    display: none;
  }

  .home-search__input {
    height: 36px;
    line-height: 36px;
  }

  .home-search__button {
    width: 36px;
    height: 36px;
    flex-basis: 36px;
  }

  .home-search-tags {
    justify-content: flex-start;
  }
}
</style>
