export function sameFrame(previous: Uint8Array | null, current: Uint8Array): boolean {
  return previous !== null && previous.length === current.length && current.every((value, index) => value === previous[index])
}

export function previewInterval(interval: number, duplicate: boolean): number {
  // JPEG feedback estimates availability; it is not the camera's nominal FPS.
  return Math.max(1000 / 12, Math.min(250, interval * (duplicate ? 1.25 : 0.95)))
}

export function previewDelay(interval: number, elapsed: number, failures: number): number {
  return failures ? Math.min(1000 * 2 ** Math.min(failures - 1, 4), 10000) : Math.max(10, interval - elapsed)
}
