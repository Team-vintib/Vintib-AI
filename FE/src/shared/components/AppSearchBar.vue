<script setup lang="ts">
const searchKeyword = defineModel<string>({ default: '' })

withDefaults(
  defineProps<{
    searchLabel: string
    placeholder: string
    popularKeywords?: string[]
    popularLabel?: string
  }>(),
  {
    popularKeywords: () => [],
    popularLabel: '인기 검색어',
  },
)

const emit = defineEmits<{
  submit: [keyword: string]
  selectKeyword: [keyword: string]
}>()

const submitSearch = () => {
  emit('submit', searchKeyword.value.trim())
}

const selectKeyword = (keyword: string) => {
  searchKeyword.value = keyword
  emit('selectKeyword', keyword)
}
</script>

<template>
  <section class="app-search-panel" :aria-label="searchLabel">
    <form class="app-search" role="search" @submit.prevent="submitSearch">
      <span class="app-search__icon" aria-hidden="true">
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
        class="app-search__input"
        type="search"
        :aria-label="searchLabel"
        :placeholder="placeholder"
      />
      <button class="app-search__button" type="submit" aria-label="검색">
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

    <div v-if="popularKeywords.length" class="app-search-tags" :aria-label="popularLabel">
      <span class="app-search-tags__label">{{ popularLabel }}</span>
      <button
        v-for="keyword in popularKeywords"
        :key="keyword"
        class="app-search-tags__item"
        type="button"
        @click="selectKeyword(keyword)"
      >
        {{ keyword }}
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.app-search-panel {
  display: grid;
  width: 100%;
  place-items: center;
  gap: var(--space-2);
  padding-top: var(--space-3);
}

.app-search {
  display: flex;
  align-items: center;
  width: min(100%, 860px);
  height: 46px;
  padding: 3px 3px 3px var(--space-4);
  border: 1px solid var(--color-search-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: none;
  transition: border-color var(--transition-base);
}

.app-search:focus-within {
  border-color: var(--color-border-underline);
}

.app-search__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  flex: 0 0 auto;
  color: var(--color-search-icon);
}

.app-search__icon svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
}

.app-search__input {
  height: var(--search-input-height);
  min-width: 0;
  border: 0;
  flex: 1;
  padding: 0 var(--space-3);
  background: transparent;
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  line-height: var(--search-input-height);
  outline: none;
}

.app-search__input::placeholder {
  color: var(--color-text-muted);
}

.app-search__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--search-input-height);
  height: var(--search-input-height);
  flex: 0 0 var(--search-input-height);
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-search-button);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
  white-space: nowrap;
}

.app-search__button svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
}

.app-search__button:hover {
  background: var(--color-search-button-hover);
}

.app-search-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  width: min(100%, 860px);
}

.app-search-tags__label {
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.app-search-tags__item {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
  transition:
    border-color var(--transition-base),
    color var(--transition-base);
}

.app-search-tags__item:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

@media (max-width: 520px) {
  .app-search {
    display: flex;
    gap: var(--space-1);
    height: 52px;
    padding: var(--space-2);
  }

  .app-search__icon {
    display: none;
  }

  .app-search__input {
    height: var(--button-height-small);
    line-height: var(--button-height-small);
  }

  .app-search__button {
    width: var(--button-height-small);
    height: var(--button-height-small);
    flex-basis: var(--button-height-small);
  }

  .app-search-tags {
    justify-content: flex-start;
  }
}
</style>
