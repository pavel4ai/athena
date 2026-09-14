import { describe, expect, it } from 'vitest'

import { logo } from '../banner.js'
import { DEFAULT_THEME } from '../theme.js'

const ATHENA_INITIAL = ['█████╗', '██╔══██╗', '███████║', '██╔══██║', '██║  ██║', '╚═╝  ╚═╝']

describe('upstream upgrade branding', () => {
  it('keeps the Athena product identity in the default theme', () => {
    expect(DEFAULT_THEME.brand.name).toBe('Athena Agent')
    expect(DEFAULT_THEME.brand.icon).toBe('⚕')
  })

  it('keeps an Athena A as the first glyph in the default logo', () => {
    const rows = logo(DEFAULT_THEME.color).map(([, text]) => text)

    expect(rows).toHaveLength(ATHENA_INITIAL.length)
    rows.forEach((row, index) => {
      expect(row.trimStart().startsWith(ATHENA_INITIAL[index]!)).toBe(true)
    })
  })
})
