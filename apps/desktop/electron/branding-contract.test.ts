import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const electronRoot = path.dirname(fileURLToPath(import.meta.url))
const desktopRoot = path.resolve(electronRoot, '..')

const packageJson = JSON.parse(
  fs.readFileSync(path.join(desktopRoot, 'package.json'), 'utf8')
)

const mainSource = fs.readFileSync(path.join(electronRoot, 'main.ts'), 'utf8')

const installerConfig = JSON.parse(
  fs.readFileSync(
    path.resolve(
      desktopRoot,
      '../bootstrap-installer/src-tauri/tauri.conf.json'
    ),
    'utf8'
  )
)

const upstreamName = ['Her', 'mes'].join('')

describe('Athena desktop distribution identity', () => {
  it('keeps Athena product branding and protocol metadata', () => {
    expect(packageJson.name).toBe('athena')
    expect(packageJson.productName).toBe('Athena')
    expect(packageJson.build.productName).toBe('Athena')
    expect(packageJson.build.executableName).toBe('Athena')
    expect(packageJson.build.artifactName).toMatch(/^Athena-/)
    expect(packageJson.build.protocols).toEqual([
      { name: 'Athena Protocol', schemes: ['athena'] }
    ])
    expect(JSON.stringify(packageJson).toLowerCase()).not.toContain(
      upstreamName.toLowerCase()
    )
  })

  it('keeps runtime branding aligned with package metadata', () => {
    expect(mainSource).toMatch(
      /const APP_NAME = process\.env\.ATHENA_DESKTOP_APP_NAME \|\| 'Athena'/
    )
    expect(mainSource).toMatch(/app\.setName\(APP_NAME\)/)
    expect(mainSource).toMatch(/applicationName: APP_NAME/)
    expect(mainSource).toMatch(/Copyright © 2026 Futurebound Corp\./)
    expect(mainSource.toLowerCase()).not.toContain(upstreamName.toLowerCase())
  })

  it('preserves upgrade-compatible desktop and setup identifiers', () => {
    expect(packageJson.build.appId).toBe('com.nousresearch.athena')
    expect(installerConfig.identifier).toBe('com.nousresearch.athena.setup')
    expect(installerConfig.productName).toBe('Athena')
    expect(installerConfig.bundle.publisher).toBe('Futurebound Corp.')
    expect(mainSource).toMatch(
      /app\.setAppUserModelId\('com\.nousresearch\.athena'\)/
    )
  })

  it('preserves the external Nous UI package dependency', () => {
    expect(packageJson.dependencies['@nous-research/ui']).toBeTruthy()
  })
})
