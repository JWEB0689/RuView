import os from 'node:os';
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import { checkSeedHealth } from './seed-client.js';

const execAsync = promisify(exec);

/**
 * Discover attached Cognitum Seed devices.
 */
export async function discoverSeed(options = {}) {
  const timeout = options.timeout || 1500;
  const candidates = new Set();

  // 1. Explicit seed URL option or environment variable
  if (options.seed) {
    candidates.add(options.seed);
  }
  if (process.env.COGNITUM_SEED_URL) {
    candidates.add(process.env.COGNITUM_SEED_URL);
  }

  // 2. Standard link-local USB Ethernet gadget addresses
  candidates.add('http://169.254.42.1');
  candidates.add('https://169.254.42.1:8443');

  // 3. Localhost (emulator/Docker/simulator)
  candidates.add('http://localhost:3000');
  candidates.add('http://localhost:8080');
  candidates.add('http://127.0.0.1:3000');

  // 4. Inspect local interfaces
  const ifaces = os.networkInterfaces();
  for (const name of Object.keys(ifaces)) {
    for (const info of ifaces[name] || []) {
      if (!info.internal && info.family === 'IPv4') {
        // Add gateway / subnet base candidates
        const parts = info.address.split('.');
        if (parts.length === 4) {
          const subnetPrefix = `${parts[0]}.${parts[1]}.${parts[2]}`;
          candidates.add(`http://${subnetPrefix}.1`);
          candidates.add(`http://${subnetPrefix}.2`);
        }
      }
    }
  }

  // 5. Try mDNS discovery if requested or available
  try {
    const mdnsHosts = await queryMdnsSeeds();
    for (const host of mdnsHosts) {
      candidates.add(host);
    }
  } catch {
    // Ignore mDNS errors
  }

  // Test candidates in parallel
  const checks = Array.from(candidates).map(async (url) => {
    try {
      const res = await checkSeedHealth(url, timeout);
      if (res.reachable) {
        return res;
      }
    } catch {
      // not reachable
    }
    return null;
  });

  const results = (await Promise.all(checks)).filter(Boolean);

  if (results.length > 0) {
    return {
      found: true,
      activeSeed: results[0].url,
      discovered: results
    };
  }

  // Fallback to default USB link-local address even if offline
  return {
    found: false,
    activeSeed: options.seed || 'http://169.254.42.1',
    discovered: [],
    hint: 'No live Seed responded. Defaulted to standard USB link-local (http://169.254.42.1).'
  };
}

/**
 * Query mDNS for _mcp._tcp or _cognitum._tcp services.
 */
async function queryMdnsSeeds() {
  const hosts = [];
  try {
    if (process.platform === 'darwin') {
      // macOS dns-sd probe with 1 second timeout
      const { stdout } = await execAsync(
        'dns-sd -B _cognitum._tcp . 2>&1 & pid=$!; sleep 1; kill $pid 2>/dev/null',
        { timeout: 2000 }
      );
      if (stdout && stdout.includes('Instance Name')) {
        hosts.push('http://seed.local:8080');
      }
    }
  } catch {
    // Fallthrough
  }
  return hosts;
}
