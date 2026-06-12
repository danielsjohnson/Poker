# Public Poker Arena Deployment

This deployment hosts the playable poker UI and game/session server only. Bot inference stays on the existing EC2 service at `/get_action`.

## Local Container Test

```powershell
$env:POKER_BOT_API_URL='http://YOUR_EC2_HOST:8000/get_action'
docker compose -f docker-compose.game.yml up --build
```

Open `http://127.0.0.1:8000`.

## DigitalOcean Droplet

Use a 1 GB shared CPU Droplet for the first deployment. With GitHub Student Developer Pack DigitalOcean credit, this is expected to cost about `$6/month` of credits.

On the Droplet:

```bash
git clone <repo-url>
cd Poker
export POKER_BOT_API_URL='http://YOUR_EC2_HOST:8000/get_action'
docker compose -f docker-compose.game.yml up --build -d
```

Open `http://DROPLET_IP:8000`.

## Runtime Responsibilities

- DigitalOcean app: React UI, game sessions, deck, betting, valid actions, community cards.
- EC2 app: model inference only, serving `/get_action`.
- Excluded: MLflow, Postgres, training containers, local model loading.
