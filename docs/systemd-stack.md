# Stack FLM via systemd

Menjalankan seluruh stack (FLM NPU server + Open WebUI) sebagai service systemd,
dengan satu perintah start/stop. **Tidak auto-start saat boot** — start manual.

## Unit

Tersimpan di `systemd/` (repo) dan di-install ke `/etc/systemd/system/`:

| Unit                 | Tipe      | Fungsi                                                    |
|----------------------|-----------|-----------------------------------------------------------|
| `flm.service`        | simple    | `flm serve qwen3.5:2b` sebagai user `hendri`, `LimitMEMLOCK=infinity` |
| `open-webui.service` | oneshot   | `docker compose up -d` / `down` di folder repo            |
| `flm-stack.target`   | target    | Pembungkus: start/stop kedua service sekaligus            |

Hubungan:

- `flm-stack.target` → `Wants=` kedua service (start target = start keduanya).
- Kedua service → `PartOf=flm-stack.target` (stop target = stop keduanya).
- `open-webui.service` → `Requires=docker.service` (docker daemon ikut dinyalakan).

## Install

```bash
sudo bash systemd/install.sh
```

Script ini meng-copy unit, `daemon-reload`, dan **sengaja tidak `enable`** —
sehingga stack tidak ikut nyala saat boot.

> Kalau suatu saat ingin auto-start saat boot:
> `sudo systemctl enable flm-stack.target`
> Untuk membatalkan: `sudo systemctl disable flm-stack.target`

## Operasi harian

```bash
sudo systemctl start flm-stack.target    # nyalakan FLM + Open WebUI
sudo systemctl stop  flm-stack.target    # matikan keduanya

systemctl status flm.service open-webui.service   # cek status
journalctl -u flm.service -f                       # log FLM (live)
journalctl -u open-webui.service -f                # log compose up/down
```

- API FLM    → <http://localhost:52625/v1>
- Open WebUI → <http://localhost:3000>

## Catatan & troubleshooting

- **Open WebUI: "model tidak ditemukan".** FLM default bind ke `127.0.0.1`,
  jadi container tidak bisa menjangkaunya lewat `host.docker.internal`. `flm.service`
  sudah memakai `--host 0.0.0.0` untuk ini. Kalau jalan `flm serve` manual untuk
  dipakai Open WebUI, tambahkan juga `--host 0.0.0.0`. Verifikasi:
  `ss -ltn | grep 52625` harus `0.0.0.0:52625` (bukan `127.0.0.1:52625`).
- **Open WebUI "no models found" padahal FLM `0.0.0.0`.** Firewall `ufw` (default
  deny incoming) men-DROP akses container -> port host. Gejala khas: uji dari
  dalam container `time out` (bukan `connection refused`). `install.sh` sudah
  menambah aturan `ufw allow from 172.16.0.0/12 to any port 52625` bila ufw aktif.
  Manual: `sudo ufw allow from 172.16.0.0/12 to any port 52625 proto tcp`.
- **Port 52625 sudah dipakai.** Pastikan tidak ada `flm serve` manual yang masih
  jalan sebelum `systemctl start` (mis. dari terminal lain). Cek:
  `ss -ltnp 'sport = :52625'`.
- **`flm.service` gagal: memlock.** Unit sudah set `LimitMEMLOCK=infinity`, jadi
  tidak tergantung re-login. Kalau tetap gagal, cek `flm validate`.
- **`open-webui.service` gagal start.** Biasanya docker daemon. Cek
  `systemctl status docker`. Unit sudah `Requires=docker.service`, jadi daemon
  semestinya ikut nyala.
- **Ganti model.** Edit `ExecStart=` di `systemd/flm.service` (mis. `qwen3.5:4b`),
  lalu `sudo bash systemd/install.sh && sudo systemctl restart flm.service`.
- **NPU device.** FLM jalan sebagai user `hendri`; `/dev/accel/accel0` ber-mode
  `crw-rw-rw-` jadi tidak butuh root.
