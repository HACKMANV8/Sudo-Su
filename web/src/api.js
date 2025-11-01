// Simple API client for the backend
const DEFAULT_BASE = 'http://127.0.0.1:8001';
const BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || DEFAULT_BASE;

export async function runPrompt(prompt, { use_csv = true, rows = 20 } = {}) {
  const res = await fetch(`${BASE_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, use_csv, rows }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

// Streaming client using EventSource (SSE)
export function runPromptStream({ prompt, use_csv = true, rows = 20 } = {}, { onMessage, onFiles, onDone, onError } = {}) {
  const url = new URL(`${BASE_URL}/run_stream`);
  url.searchParams.set('prompt', prompt);
  url.searchParams.set('use_csv', String(!!use_csv));
  url.searchParams.set('rows', String(rows));

  const es = new EventSource(url.toString());

  es.onmessage = (e) => {
    if (typeof onMessage === 'function') onMessage(e.data);
  };

  es.addEventListener('files', (e) => {
    try {
      const files = JSON.parse(e.data);
      if (typeof onFiles === 'function') onFiles(files);
    } catch (_) {
      // ignore parse error
    }
  });

  es.addEventListener('done', () => {
    if (typeof onDone === 'function') onDone();
    es.close();
  });

  es.onerror = (e) => {
    if (typeof onError === 'function') onError(e);
    es.close();
  };

  // return unsubscribe
  return () => es.close();
}

export async function approveReview(files) {
  const res = await fetch(`${BASE_URL}/review/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export async function submitReview(name, schema) {
  const res = await fetch(`${BASE_URL}/review/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, schema }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export async function fetchSpec(name) {
  // Server expects just the filename under specs/
  const fname = (name || '').split('/').pop();
  const res = await fetch(`${BASE_URL}/specs/${encodeURIComponent(fname)}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}
