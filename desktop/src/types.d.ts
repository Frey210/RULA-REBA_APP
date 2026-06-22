export {}

declare global {
  interface Window {
    ergoquipt?: {
      discoverDevices: () => Promise<DiscoveredDevice[]>
    }
  }
}

export type DiscoveredDevice = {
  cam_id: string
  hostname: string
  address: string
  port: number
  status: string
}

