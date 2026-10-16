// GET /api/external/garmin hands the garmin-sync output to a signed-in profile, read-only.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { boundPort } from './helpers.mjs';

const API = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SECRET = 'test-secret-garmin';
const cookie = uid => { const p = `${uid}:${Date.now() + 86400000}:0`; return `gymsid=${p}.${crypto.createHmac('sha256', SECRET).update(p).digest('base64url')}`; };

async function boot(t, env = {}) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gym-garmin-'));
  fs.writeFileSync(path.join(dataDir, 'secret'), SECRET, { mode: 0o600 });
  const users = ['u_g_1', 'u_g_2'].map(id => ({ id, name: id, created: new Date().toISOString() }));
  fs.writeFileSync(path.join(dataDir, 'db.json'), JSON.stringify({ users, creds: [], subs: [], invites: [] }));
  const child = spawn(process.execPath, ['server.js'], { cwd: API, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, PORT: '0', DATA_DIR: dataDir, ORIGIN: 'http://localhost:8080', RP_ID: 'localhost', ...env } });
  t.after(() => { child.kill('SIGKILL'); fs.rmSync(dataDir, { recursive: true, force: true }); });
  let log = '';
  child.stdout.on('data', d => { log += d; });
  child.stderr.on('data', d => { log += d; });
  const port = await boundPort(child, () => log);
  const get = uid => fetch(`http://127.0.0.1:${port}/api/external/garmin`, { headers: uid ? { cookie: cookie(uid) } : {} });
  return { dataDir, get };
}

test('GET /api/external/garmin: 401 signed out, empty before a sync, the file after one', async t => {
  const { dataDir, get } = await boot(t);
  assert.equal((await get()).status, 401);
  assert.deepEqual(await (await get('u_g_1')).json(), { activities: {} });

  const doc = { activities: { 123: { date: '2026-10-15', type: 'bouldering', name: 'Gym', duration_min: 90 } }, last_sync: '2026-10-16' };
  fs.writeFileSync(path.join(dataDir, 'garmin.json'), JSON.stringify(doc));
  assert.deepEqual(await (await get('u_g_1')).json(), doc);

  fs.writeFileSync(path.join(dataDir, 'garmin.json'), '{"activities": {');
  assert.equal((await get('u_g_1')).status, 503);
});

test('GET /api/external/garmin: GARMIN_UIDS limits who may read it', async t => {
  const { get } = await boot(t, { GARMIN_UIDS: 'u_g_1' });
  assert.equal((await get('u_g_1')).status, 200);
  assert.equal((await get('u_g_2')).status, 403);
});
