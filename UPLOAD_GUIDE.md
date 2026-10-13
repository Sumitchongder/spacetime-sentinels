# Publishing this repository and the game

Follow these steps once. They take about 15 minutes. Do the first commit **after** the prompt release (12 Oct 2026, 23:59 IST) and the last push **before** 16 Oct 2026, 00:00 IST.

## 1. Create the empty repository on GitHub

1. Sign in to GitHub and open <https://github.com/new>.
2. Repository name: `spacetime-sentinels`.
3. Description: `A game of low-overhead quantum error detection with spacetime codes. Every score computed with Qiskit. Qiskit Fall Fest 2026, Advanced track.`
4. Visibility: **Public**. Do **not** add a README, .gitignore or licence (they are already in this folder).
5. Click **Create repository**.

## 2. Put your username into the files

Unzip the archive, open a terminal in the `spacetime-sentinels` folder and run (replace `your-username`):

```bash
bash scripts/set_owner.sh your-username
```

This replaces the `OWNER` placeholder in the README, citation file, slides and video script so every link points to your repository and game.

## 3. First commit and push

```bash
git init
git add .
git commit -m "Spacetime Sentinels v1.0: game, Qiskit pipeline, results, report"
git branch -M main
git remote add origin https://github.com/your-username/spacetime-sentinels.git
git push -u origin main
```

If Git asks for a password, use a personal access token (GitHub → Settings → Developer settings → Personal access tokens) or sign in with GitHub Desktop or `gh auth login`.

## 4. Turn on GitHub Pages (the game link)

1. In the repository go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open the **Actions** tab. The workflow *Deploy game to GitHub Pages* runs on the push (re-run it with **Run workflow** if it ran before Pages was enabled).
4. After about a minute the game is live at **`https://your-username.github.io/spacetime-sentinels/`**.

(Alternative without Actions: Source → *Deploy from a branch*, branch `main`, folder `/docs`.)

## 5. Repository polish (2 minutes)

- **About** (gear icon on the repository page): paste the description, set Website to the Pages URL, add topics `qiskit`, `quantum-computing`, `quantum-error-correction`, `error-detection`, `qiskit-paulice`, `game`, `qiskit-fall-fest`.
- **Social preview** (Settings → General): upload `docs/assets/og.png`.
- Check the **Actions** tab: the *CI* workflow should be green.

## 6. Record and add the video

1. Record following `presentation/VIDEO_SCRIPT.md` with `presentation/slides.pdf` and the live game.
2. Upload it as an **unlisted YouTube video** or attach the MP4 to a **GitHub Release** (Releases → Draft a new release → tag `v1.0.0` → attach file). Files over 100 MB cannot be committed to git, which is why `*.mp4` is in `.gitignore`.
3. Edit `scripts/templates/README.md.in`, replace `VIDEO_LINK_PLACEHOLDER` with the link, run `cd experiments && python make_readme.py`, then:

```bash
git add README.md scripts/templates/README.md.in
git commit -m "Add video walkthrough link"
git push
```

## 7. Submit

Submit only the repository link, `https://github.com/your-username/spacetime-sentinels`, through the hackathon form before the deadline. Keep the repository public until results are announced on 18 October.

## Optional: rebuild everything yourself

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ".[dev]"
pytest                    # about 2 minutes
make reproduce            # about 2 hours on 2 cores; use WORKERS=<cores> to go faster
```
