import path from 'node:path'

/**
 * Validates a manifest/state relative path ("Assets/DLC/Shared/x.xml") and returns it normalised.
 * Relative paths are always stored with forward slashes so manifests are portable between Windows and Linux.
 * Rejects absolute paths, drive letters, "..", empty segments, backslashes and control characters so a manifest
 * can never point outside the directory it is resolved against (path traversal protection).
 */
export function checkRelPath(rel: unknown, what = 'path'): string {
  if (typeof rel !== 'string' || rel.length === 0) throw new Error(`Invalid ${what}: must be a non-empty string`)
  if (/[\u0000-\u001f\\]/.test(rel)) throw new Error(`Invalid ${what} "${rel}": control characters or backslashes`)
  if (rel.startsWith('/') || /^[a-zA-Z]:/.test(rel)) throw new Error(`Invalid ${what} "${rel}": must be relative`)
  const parts = rel.split('/')
  for (const p of parts) {
    if (p === '' || p === '.' || p === '..') throw new Error(`Invalid ${what} "${rel}": empty, "." or ".." segment`)
  }
  return parts.join('/')
}

/** Resolve a validated relative path inside root and double-check the result really is inside root. */
export function resolveInside(root: string, rel: string, what = 'path'): string {
  const clean = checkRelPath(rel, what)
  const absRoot = path.resolve(root)
  const abs = path.resolve(absRoot, ...clean.split('/'))
  const back = path.relative(absRoot, abs)
  if (back === '' || back.startsWith('..') || path.isAbsolute(back)) {
    throw new Error(`Invalid ${what} "${rel}": escapes ${absRoot}`)
  }
  return abs
}

/** All ancestor directories of a relative path, deepest first: "a/b/c.txt" -> ["a/b", "a"]. */
export function relAncestors(rel: string): string[] {
  const parts = rel.split('/')
  const out: string[] = []
  for (let i = parts.length - 1; i > 0; i--) out.push(parts.slice(0, i).join('/'))
  return out
}

export function samePath(a: string, b: string): boolean {
  const na = path.resolve(a)
  const nb = path.resolve(b)
  return process.platform === 'win32' ? na.toLowerCase() === nb.toLowerCase() : na === nb
}
