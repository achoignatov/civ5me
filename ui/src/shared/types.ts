// Types shared by the main process, the preload bridge and the React renderer.
// Only plain data crosses the IPC boundary: no functions, no fs handles.

/** Id of the baseline configuration. Every other configuration id is a mod id. */
export const VANILLA_ID = 'vanilla'

/** 'cwd': the folder the app was started from / is in; 'default': a standard Steam location. */
export type GameSource = 'cwd' | 'default'

export interface GameInfo {
  found: boolean
  /** Absolute path of the detected installation (shown to the user). */
  path: string | null
  source: GameSource | null
  /** Only when found = false: a folder that contains Civilization V but can't be used (e.g. no Brave New World). */
  problem: string | null
  /** Folders that were checked, in order (shown when nothing was found). */
  searched: string[]
}

export interface ConfigurationInfo {
  id: string
  name: string
  version: string | null
  description: string | null
  /** Mod files are missing or don't match the manifest; switching to it is impossible. */
  unavailable: string | null
  /** Development: the mod is rebuilt from the repository (working tree) before every install. */
  rebuildsFromSource: boolean
}

export type ActiveKind = 'no-game' | 'vanilla' | 'mod' | 'unknown'

export interface ActiveState {
  kind: ActiveKind
  /** Mod id when kind = 'mod'. */
  modId: string | null
  /** Short human readable label, e.g. "MiddleEarth MOD". */
  label: string
  /** Explanations (why unknown, notes about leftovers, outdated builds, ...). */
  details: string[]
}

export interface AppStatus {
  game: GameInfo
  configurations: ConfigurationInfo[]
  active: ActiveState
  busy: boolean
}

export interface Progress {
  phase: string
  done: number
  total: number
}

export interface OperationResult {
  ok: boolean
  message: string
  warnings: string[]
  status: AppStatus
}

/** The API the preload script exposes on window.civ5mm. */
export interface ManagerApi {
  getStatus(): Promise<AppStatus>
  /** Re-run detection and re-verify the installed files. */
  refresh(): Promise<AppStatus>
  switchTo(configurationId: string): Promise<OperationResult>
  /** True while Civilization V is running (the UI polls this every 5 seconds). */
  isGameRunning(): Promise<boolean>
  onProgress(listener: (p: Progress) => void): () => void
}
