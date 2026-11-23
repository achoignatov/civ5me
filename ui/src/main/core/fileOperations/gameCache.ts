import fs from 'node:fs/promises'
import path from 'node:path'
import { isErrno } from './hash'
import { describeFsError } from './errors'

/**
 * Civ V caches the combined game database in Documents/My Games/Sid Meier's Civilization 5/cache. After DLC
 * files change, a stale cache can keep the old data, so the cache is emptied after each switch.
 * The game rebuilds it on the next start. Instead of deleting it, the folder is moved to
 * <dataDir>/game-cache-previous (replacing the previous one), so nothing is lost if the user needs it.
 * Returns a note for the user.
 */
export async function clearGameCache(candidates: string[], dataDir: string): Promise<string> {
  let cacheDir: string | null = null
  for (const c of candidates) {
    try {
      if ((await fs.stat(c)).isDirectory()) {
        cacheDir = c
        break
      }
    } catch {
      /* not there */
    }
  }
  if (!cacheDir) {
    return `The game's cache folder was not found (looked in: ${candidates.join(', ')}). If you have started the game before, empty "Documents/My Games/Sid Meier's Civilization 5/cache" manually.`
  }
  const keep = path.join(dataDir, 'game-cache-previous')
  try {
    await fs.rm(keep, { recursive: true, force: true })
    try {
      await fs.rename(cacheDir, keep)
    } catch (e) {
      if (!isErrno(e, 'EXDEV')) throw e
      // different disk: copy, then empty the original
      await fs.cp(cacheDir, keep, { recursive: true })
      await fs.rm(cacheDir, { recursive: true, force: true })
    }
    await fs.mkdir(cacheDir, { recursive: true })
  } catch (e) {
    return `The game cache could not be cleared (${describeFsError(e, 'move', cacheDir)}). Close the game and empty "${cacheDir}" manually.`
  }
  return 'The game cache was emptied; the game rebuilds it on the next start.'
}
