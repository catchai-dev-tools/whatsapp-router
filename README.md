# WhatsApp Router

A minimal WhatsApp webhook router for Meta, forwarding all incoming messages to n8n, with a simple web UI for account management. Configurable for multiple WhatsApp accounts. No DB required, config stored per-appid as JSON files.

## Features
- Listens for WhatsApp webhook messages from Meta (per appid)
- Handles webhook verification (Meta challenge)
- Forwards all messages to a configured n8n webhook URL (per appid)
- Web UI to add/edit/delete WhatsApp accounts (`/accounts`)
- Logs all message traffic (viewable in UI)
- Simple config: one JSON file per appid
- Dockerized for easy deployment

---

## Quick Start (Development)

### 1. Create and activate a Python virtual environment
```sh
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```sh
pip install -r requirements.txt
```

### 3. Run the Flask app
```sh
source venv/bin/activate
```

The app will be available at: [http://localhost:5000/accounts](http://localhost:5000/accounts)

### 3. Expose your local server to the internet with Cloudflare Tunnel

#### a) Install cloudflared
[Download from Cloudflare](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

#### b) Authenticate cloudflared (one-time)
```sh
cloudflared tunnel login
```

#### c) Start a tunnel to your local server
```sh
cloudflared tunnel --url http://localhost:5000
```

- The command will print a public `https://randomstring.trycloudflare.com` URL.
- Use this URL as your webhook endpoint in Meta and for n8n (e.g., `https://randomstring.trycloudflare.com/webhook/<appid>`)

### 4. Configure WhatsApp Accounts
- Go to `/accounts` in your browser.
- Add your appid, secret, verify token, and n8n webhook URL.
- Each WhatsApp appid gets its own webhook at `/webhook/<appid>`.

### 5. Logs
- All incoming and outgoing messages are logged and viewable at the bottom of the `/accounts` page.

---

## Docker (Optional)

You can also run everything in Docker:
```sh
docker-compose up --build
```

But for development, CLI cloudflared is recommended for easy auth and tunnel management.

---

## File Structure
- `app.py` – Main Flask app (API, UI, config, logging)
- `requirements.txt` – Python dependencies
- `Dockerfile` – For containerizing the app
- `docker-compose.yml` – (Optional) For running Flask and cloudflared together
- `config_<appid>.json` – One per WhatsApp account

---

## FAQ
- **How do I update the n8n webhook URL for an account?**
  - Edit it in the `/accounts` UI and save.
- **How do I delete an account?**
  - Use the Delete button in the `/accounts` UI.
- **Where are configs stored?**
  - As `config_<appid>.json` files in the app directory.
- **How do I see logs?**
  - At the bottom of the `/accounts` page.

---

## Production
For production, use a named Cloudflare Tunnel and mount credentials (see Cloudflare docs), or deploy behind a reverse proxy.
