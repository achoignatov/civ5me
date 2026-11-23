import { useCallback, useEffect, useState } from 'react'
import { VANILLA_ID, type AppStatus, type Progress } from '@shared/types'

// StrictMode runs effects twice in development (state is kept); run the startup sequence only once.
let started = false

const GAME_POLL_MS = 5000

export interface Message {
  ok: boolean
  text: string
  warnings: string[]
}

/** The operation in progress. `target` is the configuration being activated (null: not a switch, e.g. re-check). */
export interface Working {
  label: string
  target: string | null
}

/** All communication with the main process goes through window.civ5mm (see src/preload). */
export function useManager() {
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [working, setWorking] = useState<Working | null>({ label: 'Checking the game installation…', target: null })
  const [progress, setProgress] = useState<Progress | null>(null)
  const [message, setMessage] = useState<Message | null>(null)
  const [gameRunning, setGameRunning] = useState(false)

  useEffect(() => window.civ5mm.onProgress(setProgress), [])

  // Is Civilization V running? Checked now and every 5 seconds; switching is locked while it is.
  useEffect(() => {
    let alive = true
    const check = () =>
      window.civ5mm.isGameRunning().then(
        (r) => alive && setGameRunning(r),
        () => {}
      )
    void check()
    const t = setInterval(check, GAME_POLL_MS)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const run = useCallback(async (w: Working, fn: () => Promise<void>) => {
    setWorking(w)
    setProgress(null)
    try {
      await fn()
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : String(e), warnings: [] })
    } finally {
      setWorking(null)
      setProgress(null)
    }
  }, [])

  const refresh = useCallback(
    () => run({ label: 'Checking the game installation…', target: null }, async () => setStatus(await window.civ5mm.refresh())),
    [run]
  )

  useEffect(() => {
    if (started) return
    started = true
    // Startup only detects and inspects (read-only). Switching always waits for the user to click a tile.
    void refresh()
  }, [refresh])

  const switchTo = useCallback(
    (id: string, name: string) =>
      run({ label: id === VANILLA_ID ? `Restoring ${name}…` : `Activating ${name}…`, target: id }, async () => {
        const r = await window.civ5mm.switchTo(id)
        setStatus(r.status)
        setMessage({ ok: r.ok, text: r.message, warnings: r.warnings })
      }),
    [run]
  )

  return { status, working, progress, message, gameRunning, refresh, switchTo }
}
