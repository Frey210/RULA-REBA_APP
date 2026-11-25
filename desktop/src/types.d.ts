export {}

declare global {
  interface Window {
    ergoquipt?: {
      discoverDevices: (hostnames?: string[]) => Promise<DiscoveredDevice[]>
      pairDevice: (payload: {
        baseUrl: string
        pairingCode: string
        backendUrl: string
      }) => Promise<{ status: string; cam_id: string }>
      backendUrlForDevice: (payload: {
        baseUrl: string
        backendUrl: string
      }) => Promise<string>
      networkStatus: (payload: { baseUrl: string }) => Promise<EdgeNetworkStatus>
      scanWifi: (payload: { baseUrl: string }) => Promise<{ networks: WifiNetwork[] }>
      connectWifi: (payload: {
        baseUrl: string
        ssid: string
        password: string
      }) => Promise<{ status: string; ssid: string }>
    }
  }
}

export type DiscoveredDevice = {
  device_id?: string
  cam_id: string
  hostname: string
  address: string
  port: number
  status: string
  paired: boolean
  baseUrl: string
}

export type NetworkInterfaceStatus = {
  interface: string
  state: string | null
  connection: string | null
  address: string | null
}

export type EdgeNetworkStatus = {
  ethernet_mode?: { available: boolean; mode: string; pending: boolean; target?: string; result?: string }
  wifi: NetworkInterfaceStatus
  ethernet: NetworkInterfaceStatus
  hotspot: boolean
  hotspot_ssid: string
  direct_lan_address: string
  provisioning: { state: string; ssid: string | null; error: string | null }
}

export type WifiNetwork = {
  ssid: string
  signal: number
  security: string
  connected: boolean
}
