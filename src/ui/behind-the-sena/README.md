Behind-The-Sena (BTS) React + Tailwind + Electron UI

Quickstart (development)

1. From the BTS folder, install dependencies:

```bash
cd src/ui/behind-the-sena
npm install
```

2. Start Vite dev server in one terminal:

```bash
npm run dev
```

3. Start Electron in another terminal (loads Vite dev server):

```bash
npm run electron
```

Notes

- BTS expects the Sena API to be running at `http://127.0.0.1:8000`.
- In dev you run Vite and Electron separately. For production, run `npm run build` then `npm run start` to load the built files.
- For packaging, use `electron-builder` or similar tools.
