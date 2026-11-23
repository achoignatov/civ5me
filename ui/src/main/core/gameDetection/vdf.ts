/**
 * Minimal reader for Steam's libraryfolders.vdf (Valve KeyValues text format).
 * We only need the "path" value of every library entry, so this tokenises quoted strings and braces and
 * collects every value whose key is "path".
 */
export function parseLibraryFolders(text: string): string[] {
  const tokens: string[] = []
  const re = /"((?:\\.|[^"\\])*)"|([{}])/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) tokens.push(m[2] ?? unescape(m[1]))
  const out: string[] = []
  for (let i = 0; i + 1 < tokens.length; i++) {
    if (tokens[i].toLowerCase() === 'path' && tokens[i + 1] !== '{' && tokens[i + 1] !== '}') out.push(tokens[i + 1])
  }
  return out
}

function unescape(s: string): string {
  return s.replace(/\\(.)/g, (_, c: string) => (c === 'n' ? '\n' : c === 't' ? '\t' : c))
}
