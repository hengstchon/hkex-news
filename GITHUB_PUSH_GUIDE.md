# Pushing to GitHub

## Step 1: Initialize Git Repository

```bash
git init
```

## Step 2: Stage Files

```bash
# Add all files except those in .gitignore
git add .

# Check what will be committed
git status
```

**Files that will be committed:**
- hkex_monitor.py
- run.sh
- requirements.txt
- config.json.example
- .gitignore
- LICENSE
- README.md
- Makefile
- GITHUB_PUSH_GUIDE.md

**Files that will NOT be committed (in .gitignore):**
- config.json (contains your private credentials!)
- listings_state.json
- hkex_monitor.log
- __pycache__/
- .venv/

## Step 3: Create Initial Commit

```bash
git commit -m "Initial commit: HKEX new listings monitor with Telegram alerts"
```

## Step 4: Create GitHub Repository

### Option A: Via GitHub CLI (gh)

```bash
# Install gh if not already installed
brew install gh

# Login to GitHub
gh auth login

# Create repository and push
git branch -M main
gh repo create hkex-news --public --source=. --push
```

### Option B: Via GitHub Web + Manual Push

1. Go to https://github.com/new
2. Repository name: `hkex-news`
3. Set to Public or Private
4. Click "Create repository"
5. Follow the push instructions:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/hkex-news.git
git push -u origin main
```

## Step 5: Verify

Visit `https://github.com/YOUR_USERNAME/hkex-news` to see your code!

## Step 6: Keep Sensitive Data Safe

**NEVER commit config.json!** The .gitignore already protects it, but always verify:

```bash
git status
```

If you accidentally see `config.json` as modified or staged, unstage it:
```bash
git reset config.json
git checkout config.json  # If needed
```

## Updating Your Repo

After making changes:

```bash
git add .
git commit -m "Description of changes"
git push origin main
```

## Adding Collaborators

If you want others to use/contribute:

1. Go to GitHub repo → Settings → Manage access
2. Click "Invite a collaborator"
3. Add their GitHub username
