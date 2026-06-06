# Dokumentasi

Kumpulan dokumentasi proyek LLM di laptop ini (NPU/CachyOS).

## Daftar isi

- [Menjalankan LLM di NPU (FastFlowLM)](npu-llm-fastflowlm.md) — instalasi FLM,
  fix memlock (permanent & sementara), serve API di :52625, dan Open WebUI.
- [Stack FLM via systemd](systemd-stack.md) — unit `flm.service`,
  `open-webui.service`, `flm-stack.target`; install, start/stop, log.
  Tidak auto-start saat boot.
