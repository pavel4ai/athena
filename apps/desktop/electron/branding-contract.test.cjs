const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

const desktopRoot = path.resolve(__dirname, '..')
const packageJson = JSON.parse(
  fs.readFileSync(path.join(desktopRoot, 'package.json'), 'utf8')
)
const mainSource = fs.readFileSync(path.join(__dirname, 'main.cjs'), 'utf8')
const installerConfig = JSON.parse(
  fs.readFileSync(
    path.resolve(desktopRoot, '../bootstrap-installer/src-tauri/tauri.conf.json'),
    'utf8'
  )
)
const upstreamName = ['Her', 'mes'].join('')

test('desktop package keeps Athena product branding', () => {
  assert.equal(packageJson.name, 'athena')
  assert.equal(packageJson.productName, 'Athena')
  assert.equal(packageJson.build.productName, 'Athena')
  assert.equal(packageJson.build.executableName, 'Athena')
  assert.match(packageJson.build.artifactName, /^Athena-/)
  assert.deepEqual(packageJson.build.protocols, [
    { name: 'Athena Protocol', schemes: ['athena'] }
  ])
  assert.equal(
    JSON.stringify(packageJson).toLowerCase().includes(upstreamName.toLowerCase()),
    false
  )
})

test('desktop runtime branding matches package metadata', () => {
  assert.match(mainSource, /const APP_NAME = 'Athena'/)
  assert.match(mainSource, /app\.setName\(APP_NAME\)/)
  assert.match(mainSource, /applicationName: APP_NAME/)
  assert.match(mainSource, /Copyright © \d{4} Futurebound Corp\./)
  assert.equal(mainSource.toLowerCase().includes(upstreamName.toLowerCase()), false)
})

test('desktop and setup identifiers remain upgrade compatible', () => {
  assert.equal(packageJson.build.appId, 'com.nousresearch.athena')
  assert.equal(installerConfig.identifier, 'com.nousresearch.athena.setup')
  assert.equal(installerConfig.productName, 'Athena')
  assert.equal(installerConfig.bundle.publisher, 'Futurebound Corp.')
  assert.match(
    mainSource,
    /app\.setAppUserModelId\('com\.nousresearch\.athena'\)/
  )
})

test('desktop keeps the Nous UI kit as an external dependency', () => {
  assert.ok(packageJson.dependencies['@nous-research/ui'])
})
