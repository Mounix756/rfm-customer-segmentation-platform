import http from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, extname } from "node:path";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

const api = process.env.RFM_API_URL || "http://127.0.0.1:8000";
const webhook =
  process.env.N8N_WEBHOOK_URL || "http://127.0.0.1:5678/webhook/rfm-chat";
const secret = process.env.SESSION_SECRET || randomBytes(32).toString("hex");
const sign = (value) =>
  createHmac("sha256", secret).update(value).digest("hex");
const routes = new Set([
  "model-info",
  "tableau-synthese-segments",
  "rfm-clients-segments",
  "recommandations-segments",
  "evaluation-k",
  "choix-k",
  "sensibilite-retours",
  "comparaison-segmentations",
]);
const json = (res, status, body) => {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(body));
};
const root = resolve("dist");
const mime = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
};

http
  .createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");
      if (url.pathname === "/api/chat" && req.method === "POST") {
        if (
          req.headers.origin &&
          new URL(req.headers.origin).host !== req.headers.host
        )
          return json(res, 403, { error: "Origine non autorisée." });
        if (!process.env.N8N_WEBHOOK_TOKEN)
          return json(res, 503, {
            error:
              "L'assistant n'est pas configuré. Renseignez le jeton n8n côté serveur.",
          });
        let raw = "";
        for await (const chunk of req) {
          raw += chunk;
          if (Buffer.byteLength(raw) > 12000)
            return json(res, 413, { error: "Message trop volumineux." });
        }
        let body;
        try {
          body = JSON.parse(raw);
        } catch {
          return json(res, 400, { error: "JSON invalide." });
        }
        if (
          !body ||
          typeof body.message !== "string" ||
          !body.message.trim() ||
          body.message.trim().length > 2000 ||
          !/^[A-Za-z0-9_-]{8,128}$/.test(body.sessionId || "")
        )
          return json(res, 400, { error: "Message ou session invalide." });
        const cookie =
          (req.headers.cookie || "")
            .split("; ")
            .find((v) => v.startsWith("rfm_browser="))
            ?.slice(12) || "";
        let [browser, signature] = cookie.split(".");
        const expected = sign(browser || "");
        if (
          !signature ||
          signature.length !== expected.length ||
          !timingSafeEqual(Buffer.from(signature), Buffer.from(expected))
        ) {
          browser = randomBytes(24).toString("hex");
          res.setHeader(
            "Set-Cookie",
            `rfm_browser=${browser}.${sign(browser)}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000${process.env.COOKIE_SECURE === "true" ? "; Secure" : ""}`,
          );
        }
        const upstream = await fetch(webhook, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-RFM-Token": process.env.N8N_WEBHOOK_TOKEN,
          },
          body: JSON.stringify({
            message: body.message.trim(),
            sessionId: sign(`${browser}:${body.sessionId}`),
          }),
          signal: AbortSignal.timeout(310000),
        });
        if (!upstream.ok)
          return json(res, 502, {
            error:
              "L'assistant est indisponible. Vérifiez la publication et les credentials n8n.",
          });
        const payload = await upstream.json();
        if (!payload.ok || typeof payload.answer !== "string")
          return json(res, 502, { error: "Réponse de l'assistant invalide." });
        return json(res, 200, {
          ok: true,
          answer: payload.answer,
          sessionId: body.sessionId,
        });
      }
      if (url.pathname === "/api/predict" && req.method === "POST") {
        let raw = "";
        for await (const chunk of req) {
          raw += chunk;
          if (Buffer.byteLength(raw) > 4096)
            return json(res, 413, { error: "Requête trop volumineuse." });
        }
        let body;
        try {
          body = JSON.parse(raw);
        } catch {
          return json(res, 400, { error: "JSON invalide." });
        }
        const upstream = await fetch(new URL("/predict", api), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(15000),
        });
        if (!upstream.ok)
          return json(res, upstream.status, {
            error:
              upstream.status === 422
                ? "Vérifiez les valeurs : récence entière positive ou nulle, fréquence entière positive et montant positif en livres sterling."
                : "Le modèle de classement est indisponible.",
          });
        return json(res, 200, await upstream.json());
      }
      if (url.pathname.startsWith("/api/")) {
        const path = url.pathname.slice(5);
        if (
          req.method !== "GET" ||
          !(routes.has(path) || /^segments\/[^/]+$/.test(path))
        )
          return json(res, 404, { error: "Route inconnue." });
        const target = new URL(`/${path}`, api);
        for (const key of ["limit", "offset", "segment"])
          if (url.searchParams.has(key))
            target.searchParams.set(key, url.searchParams.get(key));
        const upstream = await fetch(target, {
          signal: AbortSignal.timeout(15000),
        });
        if (!upstream.ok)
          return json(res, upstream.status, {
            error: "Données indisponibles pour cette sélection.",
          });
        return json(res, 200, await upstream.json());
      }
      if (req.method !== "GET")
        return json(res, 405, { error: "Méthode non autorisée." });
      const file = resolve(
        root,
        "." +
          decodeURIComponent(
            url.pathname === "/" ? "/index.html" : url.pathname,
          ),
      );
      if (!file.startsWith(root + "/"))
        return json(res, 404, { error: "Introuvable." });
      let data;
      try {
        data = await readFile(file);
      } catch {
        return json(res, 404, {
          error: "Fichier introuvable. Exécutez npm run build.",
        });
      }
      res.writeHead(200, {
        "Content-Type": mime[extname(file)] || "application/octet-stream",
        "X-Content-Type-Options": "nosniff",
      });
      res.end(data);
    } catch {
      json(res, 502, {
        error:
          "Connexion au service impossible. Vérifiez son démarrage et réessayez.",
      });
    }
  })
  .listen(
    Number(process.env.PORT || 3001),
    process.env.HOST || "127.0.0.1",
    () => console.log("Serveur RFM prêt"),
  );
