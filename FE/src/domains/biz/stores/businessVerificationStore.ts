import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'

import type { BusinessVerificationStatus } from '@/domains/biz/api/businessVerification'

const STORAGE_KEY = 'vidtib:business-verification-submission'

export interface BusinessCertificateSummary {
  name: string
  size: number
  type: string
}

export interface BusinessVerificationSubmission {
  id: number
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificate: BusinessCertificateSummary
  certificateFile: File
  status: BusinessVerificationStatus
  submittedAt: Date
}

interface SubmissionInput {
  id: number
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificateFile: File
  status: BusinessVerificationStatus
  submittedAt: Date
}

interface StoredBusinessVerificationSubmission {
  id: number
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificate: BusinessCertificateSummary
  status: BusinessVerificationStatus
  submittedAt: string
}

export const useBusinessVerificationStore = defineStore('business-verification', () => {
  const submission = shallowRef<BusinessVerificationSubmission | null>(readStoredSubmission())

  const hasSubmission = computed(() => submission.value !== null)

  const setSubmission = (input: SubmissionInput) => {
    submission.value = {
      ...input,
      certificate: {
        name: input.certificateFile.name,
        size: input.certificateFile.size,
        type: input.certificateFile.type,
      },
    }

    writeStoredSubmission(submission.value)
  }

  const clearSubmission = () => {
    submission.value = null
    window.sessionStorage.removeItem(STORAGE_KEY)
  }

  return {
    submission,
    hasSubmission,
    setSubmission,
    clearSubmission,
  }
})

function readStoredSubmission(): BusinessVerificationSubmission | null {
  const storedSubmission = window.sessionStorage.getItem(STORAGE_KEY)

  if (!storedSubmission) {
    return null
  }

  try {
    const parsed = JSON.parse(storedSubmission) as StoredBusinessVerificationSubmission

    return {
      ...parsed,
      certificateFile: new File([], parsed.certificate.name, {
        type: parsed.certificate.type,
      }),
      submittedAt: new Date(parsed.submittedAt),
    }
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function writeStoredSubmission(submission: BusinessVerificationSubmission) {
  const storedSubmission: StoredBusinessVerificationSubmission = {
    id: submission.id,
    businessRegistrationNumber: submission.businessRegistrationNumber,
    businessName: submission.businessName,
    representativeName: submission.representativeName,
    certificate: submission.certificate,
    status: submission.status,
    submittedAt: submission.submittedAt.toISOString(),
  }

  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(storedSubmission))
}

