import type { GameInfo } from '@shared/types'

const SOURCE_LABEL: Record<string, string> = {
  cwd: 'found in the folder this app is in',
  default: 'found in the default Steam location'
}

/** Read-only: where the game is. No folder picker; when nothing is found, explain how to make the app find it. */
export function GamePath({ game, checking }: { game: GameInfo | null; checking: boolean }) {
  if (!game || (checking && !game.found)) {
    return (
      <section className="card">
        <div className="label">Civilization V installation</div>
        <div className="muted">Looking for the game…</div>
      </section>
    )
  }
  if (game.found) {
    return (
      <section className="card">
        <div className="label">Civilization V installation</div>
        <div className="path" title={game.path ?? ''}>{game.path}</div>
        {game.source && <div className="muted">{SOURCE_LABEL[game.source]}</div>}
      </section>
    )
  }
  return (
    <section className="card game-missing" role="alert">
      <div className="label">Civilization V installation</div>
      <div className="missing-title">Civilization V: Brave New World was not found</div>
      {game.problem && <p className="missing-problem">{game.problem}</p>}
      <p>
        The app looks in the folder it is in and in the default Steam location. If your game is installed somewhere
        else, put this app into the game folder:
      </p>
      <ol>
        <li>
          In Steam, open your <b>Library</b>, right-click <b>Sid Meier's Civilization V</b> and choose{' '}
          <b>Manage → Browse local files</b>. The game installation folder opens.
        </li>
        <li>Move (or copy) this Mod Manager program into that folder.</li>
        <li>Start the Mod Manager from there.</li>
      </ol>
      {game.searched.length > 0 && (
        <details>
          <summary>Folders that were checked</summary>
          <ul className="searched">
            {game.searched.map((d) => (
              <li key={d} className="path">
                {d}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
