const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_PATTERN = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+=-]{8,20}$/
const VERIFICATION_CODE_PATTERN = /^\d{6}$/

export const isRequired = (value: string) => value.trim().length > 0

export const isEmail = (value: string) => EMAIL_PATTERN.test(value.trim())

export const isSignupPassword = (value: string) => PASSWORD_PATTERN.test(value)

export const isVerificationCode = (value: string) => VERIFICATION_CODE_PATTERN.test(value)

export const isSameValue = (value: string, compareValue: string) => value === compareValue
