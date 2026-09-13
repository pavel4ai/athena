import { describe, expect, it } from 'vitest'

import {
  normalizeAthenaOpenString,
  pathFromAthenaDeepLink,
  pathFromOpenDeepLink,
  resolveAthenaOpenPath
} from './athena-open-target'

describe('normalizeAthenaOpenString', () => {
  it('accepts hash-router paths and strips a leading hash', () => {
    expect(normalizeAthenaOpenString('/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAthenaOpenString('#/index-network/intent/1')).toBe('/index-network/intent/1')
  })

  it('maps plugin-scoped athena:// deep links to the same path', () => {
    expect(normalizeAthenaOpenString('athena://index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAthenaOpenString('athena://index-network/intent/1?focus=true')).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('maps athena://open/… deep links by stripping the open host', () => {
    expect(normalizeAthenaOpenString('athena://open/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAthenaOpenString('athena://open/settings/plugins')).toBe('/settings/plugins')
  })

  it('rejects reserved athena kinds and unsafe paths', () => {
    expect(normalizeAthenaOpenString('athena://blueprint/morning-brief')).toBeNull()
    expect(normalizeAthenaOpenString('athena://plugin/install')).toBeNull()
    expect(normalizeAthenaOpenString('https://example.com/x')).toBeNull()
    expect(normalizeAthenaOpenString('/../etc/passwd')).toBeNull()
    expect(normalizeAthenaOpenString('index-network')).toBeNull()
  })
})

describe('resolveAthenaOpenPath', () => {
  it('merges structured path + params', () => {
    expect(resolveAthenaOpenPath({ path: '/index-network/intent/1', params: { focus: 'true' } })).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('resolves href the same as a bare string', () => {
    expect(resolveAthenaOpenPath({ href: 'athena://index-network/intent/1' })).toBe('/index-network/intent/1')
  })
})

describe('pathFromAthenaDeepLink', () => {
  it('builds the navigate path from a plugin-scoped deep-link payload', () => {
    expect(pathFromAthenaDeepLink('index-network', 'intent/1')).toBe('/index-network/intent/1')
  })

  it('builds the navigate path from athena://open/… payloads', () => {
    expect(pathFromOpenDeepLink('index-network/intent/1')).toBe('/index-network/intent/1')
    expect(pathFromAthenaDeepLink('open', 'agent/42')).toBe('/agent/42')
  })

  it('ignores reserved kinds', () => {
    expect(pathFromAthenaDeepLink('blueprint', 'morning-brief')).toBeNull()
    expect(pathFromAthenaDeepLink('plugin', 'install')).toBeNull()
  })
})
