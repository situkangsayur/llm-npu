# LLM di NPU — FastFlowLM + Open WebUI

Menjalankan LLM lokal di **AMD Ryzen AI 9 HX PRO 370** (NPU XDNA2) memakai
[**FastFlowLM (FLM)**](https://github.com/FastFlowLM/FastFlowLM) sebagai runtime
NPU, dengan **Open WebUI** sebagai GUI chat.

```
┌─────────────┐   http :3000    ┌──────────────────┐   http :52625   ┌──────────────┐
│  Browser    │ ───────────────►│  Open WebUI      │ ───────────────►│  FLM serve   │
│             │                 │  (Docker)        │  OpenAI-compat  │  (host, NPU) │
└─────────────┘                 └──────────────────┘                 └──────┬───────┘
                                                                            │ /dev/accel/accel0
                                                                     ┌──────▼───────┐
                                                                     │  NPU XDNA2   │
                                                                     └──────────────┘
```

> **Kenapa FLM jalan di host, bukan container?** FLM butuh akses langsung ke
> `/dev/accel/accel0` (NPU XDNA2). Container hanya untuk UI/tools yang menunjuk
> ke API FLM lewat `host.docker.internal`.

## Komponen

| Layanan      | Di mana        | Port    | Catatan                                  |
|--------------|----------------|---------|------------------------------------------|
| FLM serve    | host (native)  | `52625` | API OpenAI-compatible, model `qwen3.5:2b`|
| Open WebUI   | Docker         | `3000`  | GUI chat -> API FLM                       |

## Cara pakai

### Opsi A — via systemd (disarankan)

Sekali install (TIDAK auto-start saat boot — start manual):

```bash
sudo bash systemd/install.sh
```

Lalu kapan pun butuh:

```bash
sudo systemctl start flm-stack.target   # nyalakan FLM + Open WebUI
sudo systemctl stop  flm-stack.target   # matikan keduanya
```

Buka <http://localhost:3000>. Detail: [docs/systemd-stack.md](docs/systemd-stack.md).

### Opsi B — manual

```bash
flm serve qwen3.5:2b          # host, butuh memlock unlimited (lihat docs)
docker compose up -d          # Open WebUI
```

## Prasyarat

- `fastflowlm` + `xrt-plugin-amdxdna` terpasang, NPU terdeteksi (`flm validate`).
- `memlock` unlimited (lihat [docs/npu-llm-fastflowlm.md](docs/npu-llm-fastflowlm.md)).
  Catatan: unit `flm.service` sudah set `LimitMEMLOCK=infinity` sendiri.
- Docker + plugin `docker compose` aktif.

## Memantau NPU

XDNA2 tak terbaca monitor biasa (CPU/GPU saja). Pakai `scripts/npu-top`
(submissions/detik = aktivitas NPU) atau `xrt-smi examine -r aie-partitions`:

```bash
ln -sf "$PWD/scripts/npu-top" ~/.local/bin/npu-top   # sekali pasang
npu-top                                               # monitor live
```

## Dokumentasi

- [Menjalankan LLM di NPU (FastFlowLM)](docs/npu-llm-fastflowlm.md) — install,
  fix memlock, serve API, uji cepat.
- [Stack via systemd](docs/systemd-stack.md) — unit, install, start/stop, log.
