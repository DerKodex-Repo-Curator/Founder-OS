# Deploying Founder OS on AWS (EC2)

This guide runs the **entire** agent — Telegram bot, scheduler, SQLite brain, dashboard
API — on a small **EC2** instance. It is the AWS equivalent of
[`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md).

**Yes, this works.** No app code changes are required beyond what is already in the repo.
You deploy with Docker the same way as any Linux VPS.

---

## Before you start — card, credits, and cost

| Question | Answer |
|---|---|
| **Does AWS ask for a card?** | **Yes.** AWS requires a payment method on signup (same as Oracle). |
| **Will I be charged?** | Not if you stay inside **Free Tier** limits and set **billing alerts**. |
| **What do new accounts get?** | Typically **12 months Free Tier** (750 hrs/month of `t2.micro` or `t3.micro`) **plus** sometimes **$100–300 promotional credits** (varies by region/promotion — check your AWS Billing dashboard after signup). |
| **What will this app cost on AWS?** | **$0/month** on Free Tier if you use `t3.micro` + **Qdrant Cloud** for vectors. After Free Tier expires, a `t3.micro` is roughly **~$8–10/month** unless you stop the instance. |

> **Important:** Set a **billing alarm at $1** (Step 2 below) so you get emailed before
> anything unexpected happens. Always pick **`t3.micro`** (Free Tier eligible), not
> larger instances.

---

## Why AWS + Qdrant Cloud (recommended stack)

A `t3.micro` has only **1 GB RAM**. Running Chroma embeddings locally on that is tight.
For AWS, use:

```bash
VECTOR_BACKEND=qdrant
QDRANT_URL=https://xxxx.cloud.qdrant.io:6333
QDRANT_API_KEY=your-key
```

Sign up free at <https://cloud.qdrant.io> (also requires a card on their paid tiers,
but the **free cluster** tier exists). Vectors live in the cloud; your EC2 only runs
the Python bot + SQLite CRM — comfortably within 1 GB.

The bot uses Telegram **long-polling**, so you **do not need to open HTTP ports**
to the internet — only **SSH (22)** for you to manage the box.

---

## Step 1 — Create an AWS account

1. Go to <https://aws.amazon.com/free/> and click **Create a Free Account**.
2. Complete email, password, account name, and **payment method** (card).
3. Choose **Basic support (free)**.
4. Pick the region closest to you (e.g. `ap-south-1` Mumbai, `us-east-1` N. Virginia).
   **Stay in one region** for the whole guide.

After login, open **Billing → Credits** to see if you received promotional credits.

---

## Step 2 — Set a billing alarm (do this first)

1. **Billing → Billing preferences** → enable **Receive Free Tier Usage Alerts** and
   **Receive Billing Alerts**.
2. **CloudWatch → Alarms → Create alarm** → metric **Billing → Total Estimated Charge**.
3. Set threshold **≥ $1 USD** → create an SNS topic with your email → confirm the email.

You will get warned before meaningful charges accrue.

---

## Step 3 — Create an EC2 key pair

1. **EC2 → Network & Security → Key pairs → Create key pair**.
2. Name: `founder-os-key`, type: **RSA**, format: **`.pem`** (Mac/Linux) or **`.ppk`** (PuTTY on Windows).
3. Download and save it — you cannot download it again.

On Windows, put the `.pem` somewhere safe, e.g. `C:\Users\You\.ssh\founder-os-key.pem`.

---

## Step 4 — Launch the EC2 instance

1. **EC2 → Instances → Launch instance**.
2. Settings:

| Setting | Value |
|---|---|
| **Name** | `founder-os` |
| **AMI** | **Ubuntu Server 22.04 LTS** (64-bit x86) |
| **Instance type** | **`t3.micro`** (Free tier eligible) |
| **Key pair** | `founder-os-key` |
| **Storage** | **30 GiB** gp3 (Free Tier covers 30 GB) |

3. **Network settings → Edit:**
   - Allow **SSH (22)** from **My IP** only (not `0.0.0.0/0` if you can avoid it).
   - **Do NOT** open ports 8787, 8788, or 3000 publicly.

4. Launch instance. Copy the **Public IPv4 address** (e.g. `3.110.xx.xx`).

---

## Step 5 — SSH into the server

**Windows (PowerShell):**
```powershell
ssh -i C:\Users\You\.ssh\founder-os-key.pem ubuntu@<PUBLIC-IP>
```

**Mac/Linux:**
```bash
chmod 400 ~/.ssh/founder-os-key.pem
ssh -i ~/.ssh/founder-os-key.pem ubuntu@<PUBLIC-IP>
```

If connection times out, check the security group allows SSH from your current IP.

---

## Step 6 — Install Docker (one command)

On the EC2 instance:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and back in (or run `newgrp docker`), then verify:

```bash
docker --version
docker compose version
```

Or run the project setup script (after cloning in Step 7):

```bash
bash scripts/aws-setup.sh
```

---

## Step 7 — Deploy Founder OS

```bash
git clone <your-repo-url> founder-os && cd founder-os
cp .env.example .env
nano .env    # fill in your secrets (see below)
```

**Minimum `.env` for AWS:**

```bash
TELEGRAM_BOT_TOKEN=...
MY_TELEGRAM_USER_ID=...
GROQ_API_KEY=...          # or GEMINI / OPENAI — at least one LLM key

# Strongly recommended on t3.micro — keeps RAM usage low
VECTOR_BACKEND=qdrant
QDRANT_URL=https://xxxx.cloud.qdrant.io:6333
QDRANT_API_KEY=...

DASHBOARD_ENABLED=true
DASHBOARD_API_PORT=8788
```

Build and run:

```bash
docker compose up -d --build
docker compose logs -f          # watch startup; Ctrl-C to stop watching
```

First build takes **5–10 minutes** on a micro instance (compiling deps). Be patient.

---

## Step 8 — Verify it works

1. Message your bot on Telegram — you should get a reply.
2. On the server:
   ```bash
   docker compose ps
   docker compose logs --tail=50
   curl -s http://127.0.0.1:8788/api/health
   ```
   Health check should return `{"status":"ok",...}`.

---

## Step 9 — Access the dashboard from your laptop

The API binds to **localhost inside the container** (safe). Tunnel it:

**Windows PowerShell:**
```powershell
ssh -i C:\Users\You\.ssh\founder-os-key.pem -L 8788:127.0.0.1:8788 ubuntu@<PUBLIC-IP>
```

Leave that window open. On your PC:

```powershell
cd web
copy .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8788
npm run dev
```

Open **http://localhost:3000** — the React dashboard talks to the API through the tunnel.

---

## Step 10 — Migrate existing brain (optional)

If you already ran Founder OS on your PC and want to move your data:

1. On your PC, zip the data folder:
   ```powershell
   Compress-Archive -Path .\data -DestinationPath founder-os-data.zip
   ```
2. Copy to EC2:
   ```powershell
   scp -i C:\Users\You\.ssh\founder-os-key.pem founder-os-data.zip ubuntu@<PUBLIC-IP>:~/
   ```
3. On EC2:
   ```bash
   cd ~/founder-os
   docker compose down
   unzip ~/founder-os-data.zip -d .
   docker compose up -d
   ```
4. If switching to Qdrant, run migration before changing backend:
   ```bash
   docker compose run --rm founder-os python scripts/migrate_chroma_to_qdrant.py
   ```

---

## Updating after code changes

```bash
cd ~/founder-os
git pull
docker compose up -d --build
```

Your `data/` volume persists across rebuilds.

---

## Stopping / avoiding charges

| Action | Command / location |
|---|---|
| **Stop the bot** (no compute charge while stopped, small EBS storage charge) | `docker compose down` then EC2 → Stop instance |
| **Delete everything** | EC2 → Terminate instance + delete unattached volumes |
| **Check spend** | AWS Console → Billing → Bills |

Free Tier covers **750 hours/month** of `t3.micro` — exactly one instance running 24/7.
Do **not** launch a second instance or upgrade to `t3.small` unless you accept the cost.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| **Out of memory / container dies** | Use `VECTOR_BACKEND=qdrant`. Add swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| **Build very slow** | Normal on t3.micro. Walk away for 10 min. |
| **Bot not replying** | Check `docker compose logs`. Verify `TELEGRAM_BOT_TOKEN` and outbound internet (security group egress is open by default). |
| **SSH timeout** | Security group must allow port 22 from your IP. Instance must be **running**. |
| **Dashboard won't load** | SSH tunnel must be active. API is on **8788**, not 8787. |

---

## Quick cost comparison

| Host | Card required? | Typical cost |
|---|---|---|
| **AWS EC2 t3.micro** (this guide) | Yes | $0 first 12 mo (Free Tier), then ~$8–10/mo |
| **Oracle Always Free** | Yes | $0 forever (ARM quirks) |
| **Hetzner VPS** | Yes | ~€4/mo |
| **Your PC 24/7** | No | Electricity + RAM/CPU load |

AWS is a solid choice if you already trust AWS billing alerts and want a familiar console.
