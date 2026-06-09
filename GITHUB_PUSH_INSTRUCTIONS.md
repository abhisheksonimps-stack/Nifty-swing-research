# Is repo ko apne GitHub par kaise daalein

## Option 1 — GitHub website se (sabse aasaan, no commands)
1. github.com par jaake **New repository** banao (naam: `nifty-swing-research`).
2. "uploading an existing file" link par click karo.
3. Is folder ke saare files drag-and-drop kar do.
4. Commit. Ho gaya.

## Option 2 — Git commands se (PC par)
PC par git installed hona chahiye. Folder ke andar terminal kholo:

```bash
git init
git add .
git commit -m "Initial commit: Nifty swing research framework"
git branch -M main
git remote add origin https://github.com/<TUMHARA-USERNAME>/nifty-swing-research.git
git push -u origin main
```

`<TUMHARA-USERNAME>` ko apne GitHub username se replace karna.
Agar push ke time login maange to GitHub Personal Access Token use karna
(Settings > Developer settings > Personal access tokens).

## Repo chalane ke liye (clone ke baad ya seedha is folder me)
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_example.py
```
