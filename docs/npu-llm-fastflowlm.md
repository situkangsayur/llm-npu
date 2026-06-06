# Menjalankan LLM di NPU (FastFlowLM) — CachyOS

Catatan setup untuk menjalankan LLM di **AMD Ryzen AI 9 HX PRO 370** (NPU XDNA2)
memakai **FastFlowLM (FLM)** — runtime native XDNA2. Ollama/llama.cpp **tidak**
bisa memakai NPU (hanya CPU/GPU).

- Driver: `amdxdna`, kernel 7.0+
- API: OpenAI-compatible di port **52625**
- Model aktif: `qwen3.5:2b` (tersimpan di `~/.config/flm/models/Qwen3.5-2B-NPU2/`)

## Instalasi (sekali saja)

```bash
sudo pacman -S fastflowlm xrt-plugin-amdxdna
flm validate          # cek NPU terdeteksi
flm pull qwen3.5:2b   # download model (sudah dilakukan)
```

## Memlock — WAJIB unlimited

FLM butuh `memlock` unlimited. Default 8MB menyebabkan:
`[ERROR] Memlock limit is too low`.

### Cara PERMANEN (disarankan)

1. Buat file config (butuh sudo):

   ```bash
   echo '*    soft    memlock    unlimited
   *    hard    memlock    unlimited' | sudo tee /etc/security/limits.d/99-flm-memlock.conf
   ```

2. **Logout lalu login lagi** (re-login) agar limit baru berlaku.
   Reboot juga bisa. Limit ini TIDAK aktif sampai sesi login baru.

3. Verifikasi setelah login ulang:

   ```bash
   ulimit -l        # harus tampil 'unlimited' (bukan 8192)
   ```

4. Setelah itu jalankan server tanpa sudo:

   ```bash
   flm serve qwen3.5:2b
   ```

### Cara SEMENTARA (tanpa re-login)

Untuk satu sesi saja, tanpa mengubah config sistem. Jalankan sebagai
transient *service* (BUKAN `--scope` — systemd 260 menolak `LimitMEMLOCK`
pada scope dengan error `Unknown assignment`):

```bash
sudo systemd-run -p LimitMEMLOCK=infinity \
  --uid=$USER --setenv=HOME=$HOME \
  flm serve qwen3.5:2b
```

systemd mencetak nama unit (mis. `run-pXXXX.service`). Lihat log dengan:

```bash
journalctl -u run-pXXXX.service -f   # ganti dengan nama unit yang dicetak
```

Untuk menghentikan: `sudo systemctl stop run-pXXXX.service`

## Perintah FLM lain

```bash
flm list              # daftar model lokal
flm run qwen3.5:2b    # chat di terminal
flm serve qwen3.5:2b  # jalankan API server di :52625
```

## UI — Open WebUI (Docker)

Arahkan ke API FLM di host:

```bash
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:52625/v1 \
  -e OPENAI_API_KEY=dummy \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui ghcr.io/open-webui/open-webui:main
```

Lalu buka http://localhost:3000

## Memantau NPU (apakah benar dipakai?)

XDNA2 **tidak muncul** di monitor biasa (`btop`/`nvtop`/`radeontop` hanya CPU/GPU).
Tool resmi = `xrt-smi`:

```bash
xrt-smi examine                      # info device + firmware NPU
xrt-smi examine -r aie-partitions    # HW context + counter Submissions (naik = NPU kerja)
```

Belum ada gauge %-utilisasi seperti nvtop. Repo ini menyediakan `scripts/npu-top`
(terpasang ke `~/.local/bin/npu-top`) yang menghitung **delta Submissions/detik**:

```bash
npu-top        # interval 1 detik
npu-top 0.5    # lebih responsif
```

Saat chat di Open WebUI, status `● BUSY` dengan submissions/detik bergerak.
Setiap respons API FLM juga memuat `prefill_speed_tps` & `decoding_speed_tps`
sebagai bukti eksekusi di NPU.

## Uji cepat API

```bash
curl http://localhost:52625/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5:2b","messages":[{"role":"user","content":"halo"}]}'
```
