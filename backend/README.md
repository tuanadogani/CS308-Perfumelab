# Perfume backend — Django + PostgreSQL

Django + PostgreSQL tabanlı backend API. Aşağıdaki komutları `backend` klasöründe çalıştırın.

## Yerel geliştirme

Python 3.13 ve PostgreSQL 17 gerekir. macOS/Homebrew kurulumu:

```sh
brew install python@3.13 postgresql@17
```

Python ortamı ve paketler:

```sh
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
```

`.env.example` dosyasını `.env` adıyla kopyalayın; `DJANGO_SECRET_KEY` ve PostgreSQL bilgilerini kendinize göre doldurun. `.env` Git'e eklenmez. Yerel kurulumda bu dosya otomatik hazırlanmış olabilir; mevcut dosyayı değiştirmeden kontrol edin.

PostgreSQL çalışıyor olmalı. Yeni bir Mac'te `perfume_app` rolünü, `perfume` veritabanını ve `.env` dosyasını hazırlamak için `brew services start postgresql@17` ardından `python scripts/setup_local_db.py` kullanılabilir. Bu betik mevcut `.env`, rol veya veritabanını değiştirmez.

```sh
python manage.py check --database default
python manage.py runserver
```

`http://127.0.0.1:8000/api/health/` adresi veritabanına gerçek bir sorgu gönderir. Başarılı yanıt:

```json
{"status": "ok", "database": "connected"}
```

Veritabanına erişilemiyorsa HTTP 503 döner. Kullanıcı tabloları migration ile yönetilir; yeni kurulumlarda sunucuyu başlatmadan önce `python manage.py migrate` çalıştırın.

Bağlantı ayarları: `config/settings.py`. PostgreSQL sürücüsü olarak psycopg kullanılır: https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-notes

## Giriş API'si

Kullanıcı modeli `accounts.User` e-posta ile giriş yapar. Şifreler Django'nun parola hash mekanizmasıyla saklanır. Tabloları oluşturmak için `python manage.py migrate` çalıştırın.

İlk hesabı terminalden oluşturun (parolayı komut satırında gizli olarak sorar):

```sh
python manage.py createsuperuser
```

Bu komut yönetici hesabı oluşturur; herkese açık kayıt API'si henüz yoktur.

| İstek | Gövde / başlık | Sonuç |
| --- | --- | --- |
| `POST /api/auth/login/` | `{"email":"kullanici@example.com","password":"parolaniz"}` | `access` ve `refresh` token'ları |
| `POST /api/auth/refresh/` | `{"refresh":"REFRESH_TOKEN"}` | Yeni `access` ve yeni `refresh` |
| `GET /api/auth/me/` | `Authorization: Bearer ACCESS_TOKEN` | `id`, `email`, `first_name`, `last_name` |

POST isteklerinde `Content-Type: application/json` gönderin. Access token 15 dakika, refresh token 1 gün geçerlidir. Yenileme sonrası eski refresh tekrar kullanılamaz; frontend yeni refresh değerini saklamalıdır.

Eksik/geçersiz alanlar `400`, hatalı giriş veya geçersiz token `401`, giriş denemesi limiti `429` döndürür. Giriş ve yenileme istekleri IP başına toplam 10/dakika ile sınırlandırılır. Varsayılan sınırlandırma tek süreç belleğini kullanır; çok süreçli canlı ortamda ortak cache ve proxy ayarları gerekir.

Frontend geliştirme adresleri `.env` içindeki `CORS_ALLOWED_ORIGINS` ile virgülle ayrılarak tanımlanır. Varsayılan olarak `http://localhost:3000` ve `http://localhost:5173` kabul edilir.

Testler ayrı `test_perfume` veritabanını kullanır. Test veritabanını hazırladıktan sonra:

```sh
python manage.py test accounts --keepdb
```

Yeni kurulumlarda test veritabanını PostgreSQL yöneticisiyle uygulama rolüne ait oluşturun veya test kullanıcısına test veritabanı oluşturma yetkisi sağlayın. Uygulama rolünün günlük kullanımda veritabanı oluşturma yetkisine ihtiyacı yoktur.
