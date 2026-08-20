# zoeTrading local UI (frontend)

React + Vite source for the local-only web UI served by `python -m zoetrading.main ui`.
Built output lives in `zoetrading/ui/static/` (committed) and is served by the FastAPI
backend in `zoetrading/ui/app.py` — most users never need Node.js at all.

## Rebuild after a frontend change

```bash
cd webui
npm install
npm run build
```

This writes directly into `../zoetrading/ui/static/` (see `vite.config.js`), which is what
`zoetrading.main ui` serves.

## Dev server (hot reload against a running backend)

```bash
# terminal 1
python -m zoetrading.main ui --port 8765

# terminal 2
cd webui
npm run dev
```

`vite.config.js` proxies `/api/*` to `http://127.0.0.1:8765`, so the dev server (usually
`http://127.0.0.1:5173`) talks to the real backend without CORS.

## Scope reminder

This UI is read/launch only: status, recent decisions, backtest report, and buttons for
`bootstrap` / `healthcheck` / `scan` / `backtest`. It cannot approve an order, cannot enable
AUTO, and cannot bypass the Risk Engine — that authority stays in the MT5 EA panel. See
`PRD.md` ("Interface web locale") for the constraints this UI must keep respecting.
