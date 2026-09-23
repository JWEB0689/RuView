import test from 'node:test';
import assert from 'node:assert/strict';
import { discoverSeed } from '../src/discovery.js';
import { checkSeedHealth } from '../src/seed-client.js';

test('discovery defaults to 169.254.42.1 when no live device is reachable', async () => {
  const result = await discoverSeed({ timeout: 100 });
  assert.ok(result.activeSeed.includes('169.254.42.1'));
});

test('checkSeedHealth gracefully handles unreachable endpoints', async () => {
  const result = await checkSeedHealth('http://192.0.2.1:9999', 100);
  assert.equal(result.reachable, false);
});
