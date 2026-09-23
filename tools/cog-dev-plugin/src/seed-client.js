import http from 'node:http';
import https from 'node:https';
import { URL } from 'node:url';

/**
 * Perform a JSON HTTP request with timeout.
 */
export async function requestJson(targetUrl, options = {}) {
  const urlObj = new URL(targetUrl);
  const client = urlObj.protocol === 'https:' ? https : http;
  const timeoutMs = options.timeout || 3000;

  return new Promise((resolve, reject) => {
    const req = client.request(
      urlObj,
      {
        method: options.method || 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        timeout: timeoutMs
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => {
          body += chunk;
        });
        res.on('end', () => {
          try {
            if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
              const parsed = body ? JSON.parse(body) : {};
              resolve({ ok: true, status: res.statusCode, data: parsed });
            } else {
              resolve({
                ok: false,
                status: res.statusCode,
                error: `HTTP ${res.statusCode}: ${body || res.statusMessage}`
              });
            }
          } catch (err) {
            resolve({ ok: false, status: res.statusCode, error: err.message, raw: body });
          }
        });
      }
    );

    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timed out after ${timeoutMs}ms`));
    });

    req.on('error', (err) => {
      reject(err);
    });

    if (options.body) {
      if (typeof options.body === 'string') {
        req.write(options.body);
      } else {
        req.write(JSON.stringify(options.body));
      }
    }

    req.end();
  });
}

/**
 * Check health of a Cognitum Seed device.
 */
export async function checkSeedHealth(baseUrl, timeout = 2000) {
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  const endpoints = ['/health', '/api/v1/health', '/'];

  for (const ep of endpoints) {
    try {
      const res = await requestJson(`${cleanUrl}${ep}`, { timeout });
      if (res.ok) {
        return { reachable: true, url: cleanUrl, endpoint: ep, data: res.data };
      }
    } catch {
      // Continue to next endpoint candidate
    }
  }

  return { reachable: false, url: cleanUrl };
}

/**
 * Fetch telemetry from a Seed device.
 */
export async function fetchSeedTelemetry(baseUrl) {
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  try {
    const res = await requestJson(`${cleanUrl}/api/v1/telemetry`, { timeout: 3000 });
    return res;
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

/**
 * Fetch witness audit chain records.
 */
export async function fetchWitnessAudit(baseUrl) {
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  try {
    const res = await requestJson(`${cleanUrl}/api/v1/witness`, { timeout: 3000 });
    return res;
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
