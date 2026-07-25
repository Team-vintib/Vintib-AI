import axios from 'axios'

const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || undefined,
  headers: {
    'Content-Type': 'application/json',
  },
})

httpClient.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem('accessToken')

  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }

  return config
})

export default httpClient
