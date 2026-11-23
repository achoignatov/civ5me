import type { ActiveState } from '@shared/types'

export function ActiveConfig({ active }: { active: ActiveState | null }) {
  const kind = active?.kind ?? 'unknown'
  return (
    <section className={`card state state-${kind}`}>
      <div className="label">Currently active</div>
      <div className="state-label">{active ? active.label : 'Checking…'}</div>
      {active?.details.map((d, i) => (
        <p key={i} className="detail">
          {d}
        </p>
      ))}
    </section>
  )
}
