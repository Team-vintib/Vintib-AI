import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useWishStore = defineStore('wish', () => {
  const wishedProductIds = ref(new Set<number>())
  const knownProductIds = ref(new Set<number>())

  const wishedCount = computed(() => wishedProductIds.value.size)

  const setProductWish = (productId: number, isWished: boolean) => {
    const nextWishedProductIds = new Set(wishedProductIds.value)
    const nextKnownProductIds = new Set(knownProductIds.value)

    nextKnownProductIds.add(productId)

    if (isWished) {
      nextWishedProductIds.add(productId)
    } else {
      nextWishedProductIds.delete(productId)
    }

    wishedProductIds.value = nextWishedProductIds
    knownProductIds.value = nextKnownProductIds
  }

  const hydrateProducts = (products: Array<{ id: number; isLiked?: boolean; isWished?: boolean }>) => {
    const nextWishedProductIds = new Set(wishedProductIds.value)
    const nextKnownProductIds = new Set(knownProductIds.value)

    products.forEach((product) => {
      const isWished = product.isLiked ?? product.isWished

      if (isWished === undefined) {
        return
      }

      nextKnownProductIds.add(product.id)

      if (isWished) {
        nextWishedProductIds.add(product.id)
      } else {
        nextWishedProductIds.delete(product.id)
      }
    })

    wishedProductIds.value = nextWishedProductIds
    knownProductIds.value = nextKnownProductIds
  }

  const hydrateWishedProductIds = (productIds: number[]) => {
    const nextKnownProductIds = new Set(knownProductIds.value)

    productIds.forEach((productId) => {
      nextKnownProductIds.add(productId)
    })

    wishedProductIds.value = new Set(productIds)
    knownProductIds.value = nextKnownProductIds
  }

  const isProductWished = (productId: number, fallback = false) =>
    knownProductIds.value.has(productId) ? wishedProductIds.value.has(productId) : Boolean(fallback)

  const clear = () => {
    wishedProductIds.value = new Set()
    knownProductIds.value = new Set()
  }

  return {
    wishedProductIds,
    wishedCount,
    clear,
    hydrateProducts,
    hydrateWishedProductIds,
    isProductWished,
    setProductWish,
  }
})
