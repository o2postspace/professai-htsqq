# Server Deployment Guide

This project can be deployed to a Linux VPS with `Docker`, `Docker Compose`, and `GitHub Actions`.

## 1. Server prerequisites

Install Docker and Docker Compose on the server.

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Reconnect to the server after changing the docker group.

Create a deploy directory:

```bash
mkdir -p /home/ubuntu/apps/professai
```

## 2. GitHub Secrets

Add these repository secrets in GitHub:

- `SERVER_HOST`: server IP or domain
- `SERVER_USER`: SSH login user
- `SERVER_PORT`: usually `22`
- `SERVER_SSH_KEY`: private key contents for the server
- `SERVER_DEPLOY_DIR`: for example `/home/ubuntu/apps/professai`
- `APP_PORT`: public port for the app, for example `8050`
- `FLASK_SECRET_KEY`: random long string
- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_ACCOUNT_NO`
- `KIS_ACCOUNT_PRODUCT`: usually `01`
- `KIS_SVR`: usually `prod`

Optional:

- `KIS_PAPER_APP_KEY`
- `KIS_PAPER_APP_SECRET`
- `WEB_CONFIG_ENABLED`: keep this as `false` for a public server

## 3. Deployment flow

When code is pushed to `main` or `master`:

1. GitHub Actions builds the Docker image.
2. The image is pushed to `GHCR`.
3. The workflow uploads `docker-compose.yml` to the server.
4. The workflow writes `.env` on the server from GitHub Secrets.
5. The server runs `docker compose pull` and `docker compose up -d`.

## 4. First deploy

Push to GitHub after adding the secrets:

```bash
git add .
git commit -m "Add Docker deployment"
git push origin main
```

If your default branch is `master`, push to `master` instead.

## 5. Useful server commands

Check logs:

```bash
cd /home/ubuntu/apps/professai
docker compose logs -f web
```

Restart:

```bash
cd /home/ubuntu/apps/professai
docker compose up -d web
```

Run OHLCV update manually:

```bash
cd /home/ubuntu/apps/professai
docker compose --profile manual run --rm updater
```

## 6. Notes

- Runtime data is stored in `data/` on the server, so tokens and OHLCV CSV files survive container restarts.
- The container seeds `data/ohlcv` from the bundled `ohlcv_deploy` data on the first run.
- `WEB_CONFIG_ENABLED=false` is recommended so nobody can overwrite your brokerage keys from the public web page.
