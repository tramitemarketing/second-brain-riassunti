/**
 * brain-sync — progressi di lettura del second brain, condivisi fra i dispositivi.
 *
 * Scelta voluta: nessun login, nessuna chiave, nessuna identità. Esiste UNO stato
 * solo: chi apre il sito e legge fa salire i progressi, da qualunque dispositivo.
 * Il sito è visto in pratica solo da Divan e i dati sono innocui (quali riassunti
 * sono stati letti e a che percentuale).
 *
 *   GET  /state                -> { pages: { "/percorso.html": {n, b, p, t}, … } }
 *   POST /state  body {page,n,b}
 *        Il client manda lo stato della pagina (b = stringa di 0/1, un bit per
 *        blocco di testo). Il server lo salva così com'è: è il client a fondere
 *        i progressi locali con quelli remoti quando apre la pagina.
 *
 *   Commenti-istruzione (Divan li scrive leggendo il sito; Claude li legge a
 *   ogni /watch o a comando, li esegue e li chiude). Nessuna auth, per scelta:
 *   Claude conferma comunque con Divan prima di eseguire azioni irreversibili.
 *   GET  /commenti[?stato=nuovo]        -> [ {id, slug, testo, t, stato}, … ]
 *   POST /commenti        body {slug, testo}
 *   POST /commenti/chiudi body {id}     -> stato: 'fatto'
 */

const ORIGINI = [
  'https://tramitemarketing.github.io',
  'http://127.0.0.1:8765',
  'http://localhost:8765',
];

const CHIAVE = 'stato-globale';
const MAX_PAGINE = 500;
const MAX_BLOCCHI = 4000;

function cors(req) {
  const o = req.headers.get('Origin') || '';
  return {
    'Access-Control-Allow-Origin': ORIGINI.includes(o) ? o : ORIGINI[0],
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Cache-Control': 'no-store',
  };
}

const json = (req, data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors(req) },
  });

function percentuale(bits) {
  if (!bits.length) return 0;
  let letti = 0;
  for (const c of bits) if (c === '1') letti++;
  return Math.round((letti / bits.length) * 100);
}

export default {
  async fetch(req, env) {
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(req) });

    const url = new URL(req.url);

    // --- commenti-istruzione ---
    if (url.pathname === '/commenti') {
      if (req.method === 'GET') {
        const c = (await env.LETTURE.get('commenti', 'json')) || [];
        const solo = url.searchParams.get('stato');
        return json(req, solo ? c.filter((x) => x.stato === solo) : c);
      }
      if (req.method === 'POST') {
        let body;
        try { body = await req.json(); } catch { return json(req, { error: 'json non valido' }, 400); }
        const slug = String(body.slug || '').slice(0, 300);
        const testo = String(body.testo || '').trim();
        if (!slug || !testo || testo.length > 2000) return json(req, { error: 'dati non validi' }, 400);
        const c = (await env.LETTURE.get('commenti', 'json')) || [];
        if (c.length >= 200) return json(req, { error: 'troppi commenti' }, 413);
        const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        c.push({ id, slug, testo, t: Date.now(), stato: 'nuovo' });
        await env.LETTURE.put('commenti', JSON.stringify(c));
        return json(req, { ok: true, id });
      }
      return json(req, { error: 'metodo non ammesso' }, 405);
    }
    if (url.pathname === '/commenti/chiudi' && req.method === 'POST') {
      let body;
      try { body = await req.json(); } catch { return json(req, { error: 'json non valido' }, 400); }
      const c = (await env.LETTURE.get('commenti', 'json')) || [];
      const x = c.find((k) => k.id === String(body.id || ''));
      if (!x) return json(req, { error: 'non trovato' }, 404);
      x.stato = 'fatto';
      await env.LETTURE.put('commenti', JSON.stringify(c));
      return json(req, { ok: true });
    }

    if (url.pathname !== '/state') return json(req, { error: 'not found' }, 404);

    if (req.method === 'GET') {
      const stato = await env.LETTURE.get(CHIAVE, 'json');
      return json(req, stato || { pages: {} });
    }

    if (req.method === 'POST') {
      let body;
      try {
        body = await req.json();
      } catch {
        return json(req, { error: 'json non valido' }, 400);
      }

      const page = String(body.page || '');
      const n = Number(body.n || 0);
      const b = String(body.b || '');
      if (!page || page.length > 300 || !n || n > MAX_BLOCCHI || b.length !== n || /[^01]/.test(b)) {
        return json(req, { error: 'dati non validi' }, 400);
      }

      const stato = (await env.LETTURE.get(CHIAVE, 'json')) || { pages: {} };
      const vecchia = stato.pages[page];

      // niente scrittura se non è cambiato nulla (la quota gratuita ringrazia)
      if (vecchia && vecchia.n === n && vecchia.b === b) {
        return json(req, { p: vecchia.p, invariato: true });
      }
      if (!vecchia && Object.keys(stato.pages).length >= MAX_PAGINE) {
        return json(req, { error: 'troppe pagine' }, 413);
      }

      stato.pages[page] = { n, b, p: percentuale(b), t: Date.now() };
      await env.LETTURE.put(CHIAVE, JSON.stringify(stato));
      return json(req, { p: stato.pages[page].p });
    }

    return json(req, { error: 'metodo non ammesso' }, 405);
  },
};
