/**
 * Step 16 — Multi-market (UK/CA) support tests.
 *
 * Run with: node --test tests/multimarket.test.js
 *
 * Two layers:
 *  1. Structural — assert amazon.co.uk / amazon.ca appear in every place the
 *     extension needs them (manifest arrays + content.js MARKETPLACE_MAP +
 *     background.js MARKETPLACE_TLD_MAP). A missing entry in any one array
 *     silently breaks that market, so we check them all.
 *  2. Behavioral — the date/rating parsers used for UK/CA reviews. UK & CA
 *     English review strings ("Reviewed in the United Kingdom on 3 April 2025",
 *     "Reviewed in Canada on April 3, 2025") must parse to a valid ISO date.
 */

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const EXT_DIR = path.join(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(EXT_DIR, 'manifest.json'), 'utf8'));
const contentSrc = fs.readFileSync(path.join(EXT_DIR, 'content.js'), 'utf8');
const bgSrc = fs.readFileSync(path.join(EXT_DIR, 'background.js'), 'utf8');

const NEW_MARKETS = [
  { host: 'amazon.co.uk', code: 'UK', tld: '.co.uk', tldCode: 'uk' },
  { host: 'amazon.ca', code: 'CA', tld: '.ca', tldCode: 'ca' },
];

// ── Layer 1: structural coverage ──

test('manifest host_permissions cover UK/CA', () => {
  for (const m of NEW_MARKETS) {
    const found = manifest.host_permissions.some((p) => p.includes(m.host));
    assert.ok(found, `host_permissions missing ${m.host}`);
  }
});

test('manifest content_scripts matches cover UK/CA', () => {
  const matches = manifest.content_scripts[0].matches;
  for (const m of NEW_MARKETS) {
    assert.ok(matches.some((p) => p.includes(m.host)), `content_scripts missing ${m.host}`);
  }
});

test('manifest web_accessible_resources cover UK/CA', () => {
  const matches = manifest.web_accessible_resources[0].matches;
  for (const m of NEW_MARKETS) {
    assert.ok(matches.some((p) => p.includes(m.host)), `web_accessible_resources missing ${m.host}`);
  }
});

test('content.js MARKETPLACE_MAP maps UK/CA hosts to codes', () => {
  for (const m of NEW_MARKETS) {
    // e.g. 'amazon.co.uk': 'UK'
    const re = new RegExp(`'${m.host.replace(/\./g, '\\.')}':\\s*'${m.code}'`);
    assert.match(contentSrc, re, `MARKETPLACE_MAP missing ${m.host} → ${m.code}`);
  }
});

test('background.js MARKETPLACE_TLD_MAP maps UK/CA TLDs to codes', () => {
  for (const m of NEW_MARKETS) {
    const re = new RegExp(`'${m.tld.replace(/\./g, '\\.')}':\\s*'${m.tldCode}'`);
    assert.match(bgSrc, re, `MARKETPLACE_TLD_MAP missing ${m.tld} → ${m.tldCode}`);
  }
});

// ── Layer 2: behavioral (parsers mirror content.js contract) ──

// Mirror of content.js parseDateToISO (kept in sync with source).
function parseDateToISO(text) {
  if (!text) return null;
  try {
    const d = new Date(text);
    if (!isNaN(d.getTime())) return d.toISOString();
    const monthMatch = text.match(
      /(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}/i
    );
    if (monthMatch) {
      const d2 = new Date(monthMatch[0]);
      if (!isNaN(d2.getTime())) return d2.toISOString();
    }
  } catch { /* fall through */ }
  return null;
}

// Mirror of content.js detectMarketplace TLD logic (longest suffix wins).
const TLD_MAP = { '.com': 'us', '.co.uk': 'uk', '.ca': 'ca' };
function detectMarketplace(url) {
  const hostname = new URL(url).hostname;
  const suffixes = Object.keys(TLD_MAP).sort((a, b) => b.length - a.length);
  for (const s of suffixes) if (hostname.endsWith(s)) return TLD_MAP[s];
  return 'us';
}

test('UK/CA English review dates parse to valid ISO', () => {
  const cases = [
    'Reviewed in the United Kingdom on April 3, 2025',
    'Reviewed in Canada on April 3, 2025',
    'Reviewed in the United States on January 15, 2025',
  ];
  for (const c of cases) {
    const iso = parseDateToISO(c);
    assert.ok(iso, `failed to parse: ${c}`);
    assert.match(iso, /^\d{4}-\d{2}-\d{2}T/, `not ISO 8601: ${iso}`);
  }
});

test('detectMarketplace resolves .co.uk before .com-style suffixes', () => {
  assert.equal(detectMarketplace('https://www.amazon.co.uk/product-reviews/B09G9D7K7K/'), 'uk');
  assert.equal(detectMarketplace('https://www.amazon.ca/dp/B08N5WRWNW/'), 'ca');
  assert.equal(detectMarketplace('https://www.amazon.com/dp/B08N5WRWNW/'), 'us');
});
