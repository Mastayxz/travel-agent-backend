# Bali Travel Agent Backend

Backend API chatbot travel guide fokus wisata Bali menggunakan Google Gemini API dan Google ADK Agent SDK.

## 🌟 Fitur

- **Chatbot Interaktif** - Percakapan dengan konteks dan histori sesi
- **Otentikasi OAuth2** - Token Google OAuth2 untuk keamanan
- **Penyimpanan Histori** - Histori chat tersimpan di MongoDB
- **Google Agent SDK** - Agent berbasis Google ADK dengan Google Search tool

## 📋 Prasyarat

Pastikan sistem Anda memiliki:

- **Python 3.11+**
- **MongoDB** - Berjalan dan dapat diakses
- **Google API Keys** - Gemini API & OAuth2 credentials
- **Git** - Untuk clone repository

## 🚀 Setup & Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/username/bali-travel-agent-backend.git
cd bali-travel-agent-backend
```

### 2. Buat Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip fastapi uvicorn pymongo python-dotenv  
pip install google-auth google-auth-oauthlib google-auth-httplib2  
pip install google-adk                            
pip install httpx                                      
pip install fastapi uv
```

### 4. Konfigurasi Environment

Buat file `.env` di folder root dengan konfigurasi berikut:

```env
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret_here

# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
```

> ⚠️ **Penting:** Ganti semua placeholder dengan kredensial yang valid dari Google Cloud Console dan MongoDB Atlas.

### 5. Verifikasi MongoDB

Pastikan MongoDB sudah berjalan dan URI connection string sudah benar.

### 6. Jalankan Aplikasi

```bash
uvicorn app.main:app --reload
```

Aplikasi akan berjalan di `http://localhost:8000`




```

## 🛠️ Development

Untuk development mode:

```bash
# Install development dependencies
pip fastapi uvicorn pymongo python-dotenv  
pip install google-auth google-auth-oauthlib google-auth-httplib2  
pip install google-adk                            
pip install httpx                                      
pip install fastapi uv

# Run with auto-reload
uvicorn app.main:app --reload 
```

## 📊 Database Schema

MongoDB collections yang digunakan:

- **users** - Data pengguna dan OAuth tokens
- **histories** - histories chat

## 🔐 Keamanan

- OAuth2 authentication dengan Google
- Token validation untuk setiap request
- Rate limiting untuk API endpoints
- Input validation dan sanitization

## 🤝 Kontribusi

1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

## 📝 License



## 📞 Kontak

Project Link: [https://github.com/Mastayxz/travel-agent-backend](https://github.com/Mastayxz/travel-agent-backend)

---

⭐ **Jangan lupa beri star jika project ini membantu!**
