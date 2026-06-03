# 🚀 Web Dashboard Deployment Guide (SaaS)

Panduan ini ditujukan bagi pengguna yang ingin meng-*host* Web Dashboard (Backend & Frontend) Xerynq di VPS pribadi (misalnya menggunakan aaPanel) dan menghubungkannya dengan aman menggunakan Cloudflare Tunnels.

## 1. Persiapan VPS
Sebaiknya gunakan VPS dengan sistem operasi **Ubuntu 22.04 / 24.04**.
Tidak membutuhkan spesifikasi tinggi (RAM 1GB - 2GB sudah lebih dari cukup).

## 2. Deploy Backend (FastAPI) via aaPanel
Meskipun aaPanel memiliki fitur *Python Manager*, untuk performa dan stabilitas terbaik dengan FastAPI, sangat disarankan menggunakan eksekusi langsung (native) via Terminal menggunakan `tmux` atau `pm2`.

**Langkah Instalasi Native:**
```bash
# 1. Masuk ke folder backend
cd /www/wwwroot/api.namadomain.com/

# 2. Buat virtual environment
apt update && apt install python3.12-venv python3-pip tmux -y
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Jalankan menggunakan Tmux (agar nyala 24/7)
tmux new -s backend
source venv/bin/activate
python main.py
# Tekan Ctrl+B, lalu D untuk keluar (detach) dari tmux.
```
*Backend akan berjalan di port lokal 8000.*

## 3. Deploy Frontend (React/Vite)
Frontend Xerynq adalah *Single Page Application* (SPA) murni, sehingga tidak membutuhkan runtime Node.js di server produksi.

1. Di komputermu, masuk ke folder `trading-landing` lalu jalankan:
   ```bash
   npm run build
   ```
2. Upload seluruh isi folder `dist/` ke direktori web di VPS-mu (misal: `/www/wwwroot/app.namadomain.com`).
3. **Penting (Nginx Routing):** Masukkan pengaturan ini di file konfigurasi Nginx aaPanel (*URL Rewrite*):
   ```nginx
   location / {
     try_files $uri $uri/ /index.html;
   }
   ```
   *Ini memastikan halaman seperti `/login` atau `/dashboard` tidak mengalami error 404 saat di-reload.*

## 4. Konfigurasi Keamanan via Cloudflare Tunnels (Direkomendasikan)
Untuk alasan keamanan (terutama pada VPS berjenis NAT), sangat disarankan **TIDAK** membuka port secara publik, melainkan menggunakan *Cloudflare Zero Trust*.

1. Masuk ke **Cloudflare Dashboard** -> **Zero Trust** -> **Networks** -> **Tunnels**.
2. Buat Tunnel baru, lalu jalankan perintah instalasi (`cloudflared service install`) di terminal VPS-mu.
3. Tambahkan **Public Hostname**:
   - Subdomain: `api-trade` (menghindari limitasi SSL gratis pada subdomain level ke-4).
   - Domain: `namadomain.com`
   - Service: `HTTP` -> `127.0.0.1:8000` (Arahkan ke backend Python).

Dengan pengaturan ini, API dan Dashboard-mu akan langsung mendapatkan SSL gratis (HTTPS), perlindungan anti-DDoS, dan performa tinggi berkat jaringan global Cloudflare!
