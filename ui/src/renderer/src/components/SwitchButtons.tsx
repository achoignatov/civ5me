import { VANILLA_ID, type AppStatus, type Progress } from '@shared/types'
import type { Working } from '../hooks/useManager'
import bnwArt from '../assets/bnw.jpg'
import middleEarthArt from '../assets/middleearth.jpg'

/** Artwork and display name per configuration id; unknown mods fall back to a plain tile with their own name. */
const LOOK: Record<string, { art: string; title: string }> = {
  [VANILLA_ID]: { art: bnwArt, title: 'Vanilla BNW' },
  middleearth: { art: middleEarthArt, title: 'Middle Earth' }
}

interface Props {
  status: AppStatus | null
  disabled: boolean
  /** Civilization V is running: every tile is locked (`disabled` is already true) and says why. */
  gameRunning: boolean
  working: Working | null
  progress: Progress | null
  onSwitch: (id: string, name: string) => void
}

/** One large picture tile per configuration (Vanilla first, then every registered mod). */
export function SwitchButtons({ status, disabled, gameRunning, working, progress, onSwitch }: Props) {
  if (!status) return null
  const noGame = !status.game.found
  return (
    <section className="tiles">
      {status.configurations.map((c) => {
        const look = LOOK[c.id]
        const title = look?.title ?? c.name
        const isActive = (status.active.kind === 'vanilla' && c.id === VANILLA_ID) || (status.active.kind === 'mod' && status.active.modId === c.id)
        const isTarget = working?.target === c.id
        const pct = progress && progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : null
        const classes = ['tile', isActive && 'active', isTarget && 'working', (disabled || noGame) && !isTarget && 'dimmed'].filter(Boolean).join(' ')
        return (
          <button
            key={c.id}
            className={classes}
            disabled={disabled || noGame || c.unavailable !== null}
            title={gameRunning ? 'Close Civilization V first' : (c.unavailable ?? c.description ?? '')}
            aria-pressed={isActive}
            aria-busy={isTarget}
            onClick={() => onSwitch(c.id, title)}
          >
            <span className="tile-art" style={look ? { backgroundImage: `url(${look.art})` } : undefined} />
            <span className="tile-shade" />
            {isActive && !isTarget && <span className="tile-active">Active</span>}
            {isTarget ? (
              <span className="tile-progress" aria-live="polite">
                <span className="spinner" />
                <span className="tile-phase">{progress?.phase ?? working!.label}</span>
                <progress max={100} value={pct ?? undefined} />
                {progress && progress.total > 1 && (
                  <span className="tile-count">
                    {progress.done} / {progress.total}
                  </span>
                )}
              </span>
            ) : (
              !disabled && !noGame && !c.unavailable && <span className="tile-cta">{isActive ? 'Reapply' : 'Activate'}</span>
            )}
            <span className="tile-footer">
              <span className="tile-title">{title}</span>
              {c.unavailable && <span className="tile-sub error">{c.unavailable}</span>}
              {c.rebuildsFromSource && <span className="tile-sub">rebuilds from the repository first (dev)</span>}
            </span>
          </button>
        )
      })}
    </section>
  )
}
