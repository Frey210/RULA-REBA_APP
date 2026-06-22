export {}

declare global {
  interface Window {
    ergoquipt?: {
      discoverDevices: () => Promise<DiscoveredDevice[]>
      pairDevice: (payload: {
        baseUrl: string
        pairingCode: string
        backendUrl: string
      }) => Promise<{ status: string; cam_id: string }>
      backendUrlForDevice: (payload: {
        baseUrl: string
        backendUrl: string
      }) => Promise<string>
    }
  }
}

export type DiscoveredDevice = {
  cam_id: string
  hostname: string
  address: string
  port: number
  status: string
  paired: boolean
  baseUrl: string
}
