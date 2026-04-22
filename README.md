# CDN Panel

A self-hosted file management dashboard built with Flask and Tailwind CSS. Files are stored on Cloudflare R2 and served through a custom domain. Metadata and expiration tracking are handled by MongoDB.

## Features

- Password-protected admin panel
- Drag-and-drop file uploads to Cloudflare R2
- File listing fetched directly from the R2 bucket
- CORS support via Flask-CORS
- Per-file expiration (1 day, 7 days, 30 days, 90 days, or never)
- Automatic cleanup of expired files on page load
- Copy public CDN URL to clipboard
- Delete files from both R2 and MongoDB
- Light and dark mode toggle
- Responsive layout for desktop and mobile

## Requirements

- Python 3.10+
- Node.js 18+ (for Tailwind CSS build)
- MongoDB instance (local or remote)
- Cloudflare R2 bucket with S3-compatible API credentials
- Custom domain pointed to the R2 bucket (optional but recommended)

## Setup

### 1. Clone the repository

```
git clone https://github.com/yourusername/cdn-panel.git
cd cdn-panel
```

### 2. Create a virtual environment

```
python -m venv env
env\Scripts\activate        # Windows
source env/bin/activate     # Linux / macOS
```

### 3. Install Python dependencies

```
pip install -r requirements.txt
```

### 4. Install Node dependencies

```
npm install
```

### 5. Configure environment variables

Copy the example file and fill in your values:

```
cp .env.example .env
```

| Variable               | Description                              |
|------------------------|------------------------------------------|
| `endpoint_url`         | Cloudflare R2 S3-compatible endpoint     |
| `aws_access_key_id`    | R2 API access key ID                     |
| `aws_secret_access_key`| R2 API secret access key                 |
| `MONGO_URI`            | MongoDB connection string                |
| `SECRET_KEY`           | Flask session secret key                 |
| `ADMIN_PASSWORD`       | Password for the login page              |
| `BUCKET_NAME`          | R2 bucket name (default: `cdn`)          |
| `CDN_DOMAIN`           | Custom domain for public file URLs       |

### 6. Build Tailwind CSS

```
npm run tw
```

This starts the Tailwind CLI in watch mode. For a one-time build:

```
npx @tailwindcss/cli -i ./static/src/input.css -o ./static/dist/output.css
```

### 7. Run the application

```
python main.py
```

The app will be available at `http://127.0.0.1:5000`.

## Project Structure

```
.
├── main.py                  # Flask application
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
├── .env.example             # Template for .env
├── package.json             # Node dependencies (Tailwind CSS)
├── static/
│   ├── src/
│   │   └── input.css        # Tailwind source with theme variables
│   └── dist/
│       └── output.css       # Compiled CSS (generated)
└── templates/
    ├── login.html           # Login page
    └── index.html           # Dashboard page
```

## Hosting

### Option A: VPS (Recommended)

Deploy on any Linux VPS (Ubuntu, Debian, etc.) behind Nginx and Gunicorn.

1. Set up the project on your server following the steps above.

2. Install Gunicorn:

```
pip install gunicorn
```

3. Run with Gunicorn:

```
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

4. Configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name panel.yourdomain.com;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

5. Enable HTTPS with Certbot:

```
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d panel.yourdomain.com
```

6. Create a systemd service at `/etc/systemd/system/cdn-panel.service`:

```ini
[Unit]
Description=CDN Panel
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/cdn-panel
ExecStart=/path/to/cdn-panel/env/bin/gunicorn -w 4 -b 127.0.0.1:8000 main:app
Restart=always
EnvironmentFile=/path/to/cdn-panel/.env

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl enable cdn-panel
sudo systemctl start cdn-panel
```

### Option B: Docker

1. Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "main:app"]
```

2. Build and run:

```
docker build -t cdn-panel .
docker run -d -p 8000:8000 --env-file .env cdn-panel
```

### Option C: PaaS (Railway, Render, Fly.io)

1. Push the repository to GitHub.
2. Connect the repository to your chosen platform.
3. Set all environment variables from `.env.example` in the platform dashboard.
4. Set the start command to `gunicorn -w 4 -b 0.0.0.0:$PORT main:app`.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
