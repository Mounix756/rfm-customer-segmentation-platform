import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";

test("relais : contrat, secret serveur, isolation et refus des routes libres", async () => {
  const received = [];
  const queries = [];
  const upstream = http
    .createServer(async (req, res) => {
      queries.push(req.url);
      if (req.url.startsWith('/clients/export')) {
        res.writeHead(200, {'Content-Type':'text/csv; charset=utf-8','X-Total-Count':'2'});
        res.end('\ufeffCustomerID;Monetary\n12345;100\n12346;200\n');
        return;
      }
      let raw = "";
      for await (const part of req) raw += part;
      res.setHeader("Content-Type", "application/json");
      if (req.url === '/predict' && JSON.parse(raw).observation_start === 'invalid') {
        res.statusCode=422;
        res.end(JSON.stringify({detail:[{msg:'Value error, La fenêtre est invalide.'}]}));
        return;
      }
      if (req.method === "POST") {
        received.push({
          ...JSON.parse(raw),
          token: req.headers["x-rfm-token"],
        });
        res.end(JSON.stringify({ ok: true, answer: "Bonjour." }));
      } else res.end(JSON.stringify({ data: [{ Segment: "Test" }] }));
    })
    .listen(0, "127.0.0.1");
  await once(upstream, "listening");
  const probe = http.createServer().listen(0, "127.0.0.1");
  await once(probe, "listening");
  const port = probe.address().port;
  await new Promise((r) => probe.close(r));
  const target = `http://127.0.0.1:${upstream.address().port}`;
  const child = spawn(process.execPath, ["server.mjs"], {
    cwd: new URL("..", import.meta.url),
    env: {
      ...process.env,
      HOST: "127.0.0.1",
      PORT: String(port),
      RFM_API_URL: target,
      N8N_WEBHOOK_URL: target,
      N8N_WEBHOOK_TOKEN: "test-only",
      SESSION_SECRET: "test-secret",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    await Promise.race([
      once(child.stdout, "data"),
      new Promise((_, reject) => {
        const timer = setTimeout(
          () => reject(new Error("Démarrage impossible")),
          5000,
        );
        timer.unref();
      }),
    ]);
    const base = `http://127.0.0.1:${port}/api/`;
    assert.equal((await fetch(base + "tableau-synthese-segments")).status, 200);
    assert.equal((await fetch(base + "arbitrary")).status, 404);
    const send = (body, cookie, origin) =>
      fetch(base + "chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(cookie ? { cookie } : {}),
          ...(origin ? { origin } : {}),
        },
        body: JSON.stringify(body),
      });
    assert.equal(
      (await send({ message: "", sessionId: "session-test" })).status,
      400,
    );
    assert.equal(
      (
        await send(
          { message: "Bonjour", sessionId: "session-test" },
          null,
          "https://other.example",
        )
      ).status,
      403,
    );
    const first = await send({ message: "Bonjour", sessionId: "session-test" });
    const cookie = first.headers.get("set-cookie").split(";")[0];
    assert.match(first.headers.get("set-cookie"), /HttpOnly/);
    assert.deepEqual(await first.json(), {
      ok: true,
      answer: "Bonjour.",
      sessionId: "session-test",
    });
    await send({ message: "Suite", sessionId: "session-test" }, cookie);
    await send({ message: "Autre navigateur", sessionId: "session-test" });
    await send(
      { message: "Autre conversation", sessionId: "different-test" },
      cookie,
    );
    assert.equal(received[0].token, "test-only");
    assert.equal(received[0].sessionId, received[1].sessionId);
    assert.notEqual(received[0].sessionId, received[2].sessionId);
    assert.notEqual(received[0].sessionId, received[3].sessionId);
    const filtered = 'rfm-clients-segments?q=actifs&country=France&monetary_min=100&sort_by=Monetary&order=desc';
    assert.equal((await fetch(base + filtered)).status,200);
    const forwarded = new URL(queries.at(-1),'http://test');
    for (const [key,value] of new URL(filtered,'http://test').searchParams) assert.equal(forwarded.searchParams.get(key),value);
    const exported = await fetch(base + 'clients/export?country=France&monetary_min=100');
    assert.equal(exported.status,200);
    assert.match(exported.headers.get('content-type'),/text\/csv/);
    assert.match(exported.headers.get('content-disposition'),/attachment/);
    const csvBytes = Buffer.from(await exported.arrayBuffer());
    assert.deepEqual([...csvBytes.subarray(0,3)],[0xef,0xbb,0xbf]);
    assert.match(csvBytes.toString('utf8'),/12346;200/);
    assert.equal((await fetch(base+'clients/filters')).status,200);
    assert.equal((await fetch(base+'bundle-info')).status,200);
    const profile = { recency: 30, frequency: 8, monetary: 2500,
      observation_start:'2009-12-01',observation_end:'2011-12-09',reference_date:'2011-12-10',mode:'historical' };
    const prediction = await fetch(base + 'predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    assert.equal(prediction.status, 200);
    assert.deepEqual(received.at(-1), { ...profile, token: undefined });
    const invalidPeriod = await fetch(base+'predict', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...profile,observation_start:'invalid'})});
    assert.equal(invalidPeriod.status,422);
    assert.deepEqual(await invalidPeriod.json(),{error:'La fenêtre est invalide.'});
    assert.equal((await fetch(base + 'predict')).status, 404);
  } finally {
    child.kill();
    upstream.closeAllConnections();
    await new Promise((r) => upstream.close(r));
  }
});
