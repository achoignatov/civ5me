import type { Progress } from '@shared/types'
import type { Message, Working } from '../hooks/useManager'

/**
 * Result messages, plus progress for operations that don't belong to a tile (re-check, folder selection).
 * Activation/deactivation progress is shown inside the target tile instead.
 */
export function StatusBar({ working, progress, message }: { working: Working | null; progress: Progress | null; message: Message | null }) {
  if (working && working.target === null) {
    const pct = progress && progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : null
    return (
      <section className="card status" aria-live="polite">
        <div>{progress?.phase ?? working.label}</div>
        <progress max={100} value={pct ?? undefined} />
        {progress && progress.total > 1 && (
          <div className="muted">
            {progress.done} / {progress.total}
          </div>
        )}
      </section>
    )
  }
  if (working) return <section className="card status muted">{working.label}</section>
  if (!message) return <section className="card status muted">Ready.</section>
  return (
    <section className={`card status ${message.ok ? 'ok' : 'error'}`} aria-live="polite">
      <div className="msg">{message.text}</div>
      {message.warnings.length > 0 && (
        <ul>
          {message.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </section>
  )
}
