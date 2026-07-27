import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'

export interface BusinessVerificationSubmission {
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificateFile: File
  submittedAt: Date
}

type SubmissionInput = Omit<BusinessVerificationSubmission, 'submittedAt'>

export const useBusinessVerificationStore = defineStore('business-verification', () => {
  const submission = shallowRef<BusinessVerificationSubmission | null>(null)

  const hasSubmission = computed(() => submission.value !== null)

  const setSubmission = (input: SubmissionInput) => {
    submission.value = {
      ...input,
      submittedAt: new Date(),
    }
  }

  const clearSubmission = () => {
    submission.value = null
  }

  return {
    submission,
    hasSubmission,
    setSubmission,
    clearSubmission,
  }
})

