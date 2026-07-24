import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),

  routes: [
    {
      path: '/onboarding/basic-info',
      name: 'onboarding-basic-info',
      component: () =>
        import('@/views/onboarding/OnboardingBasicInfoView.vue'),
    },
  ],
})

export default router
