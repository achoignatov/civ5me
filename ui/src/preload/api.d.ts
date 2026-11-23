import type { ManagerApi } from '../shared/types'

declare global {
  interface Window {
    civ5mm: ManagerApi
  }
}
export {}
