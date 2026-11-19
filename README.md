# JochreBot Zoo: a Page Checker for Yiddish print

A small custom tool for one job: checking machine-read Yiddish print.

Built on the morning of 19 November 2026 for the AI Explorer workshop at Ohio State, as a
proof of an idea: instead of asking people to "go back and check the AI's work", build a
tool that makes the checking trivial.

## What it does

1. You drop a page image into a web page (one column works best).
2. **Jochre 3**, a free Yiddish OCR program, reads it on your own computer.
3. The page shows the image beside the text. The words the computer doubts most are
   boxed on the image and highlighted in the text.
4. Click a doubtful word: you see it zoomed in, the computer's reading, and how it would
   sound. Press Enter if it is right, or type the fix and press Enter.
5. "Confirm page" sends the checked text to an `archive/` folder with your name and the date.
   Every fix is also added to `archive/corrections.jsonl`, a file of training examples
   (image, word position, computer's reading, human's reading).

Nothing leaves your computer.

## Why it matters

- **A custom tool, not a general one.** Chat tools can do almost anything, so the method
  lives in your head. This tool does one job and carries the method for you.
- **Checking becomes trivial.** The computer says where it is unsure; you settle only those spots.
- **The work compounds.** Each fix is kept and can train the next version. Many people can
  share one queue, as volunteers do for Galaxy Zoo.
- **Easy to change.** It is two short files (`server.py`, `index.html`), written with Claude
  in about 15 minutes.

## Run it

You need Jochre 3 running on your computer (see https://gitlab.com/jochre/jochre3-ocr).

```bash
python3 server.py
```

Then open http://localhost:8765 and click "Try the 1933 sample".

## Honest limits

- A prototype: one page at a time, no user accounts, no shared queue yet.
- "Doubt" is Jochre's own confidence score, ranked within the page (the least certain quarter
  is marked "unsure"). On rough scans, most words score low.
- The sample is a notice from *Grodner Moment* (Grodno, 18 August 1933), public domain,
  from Wikimedia Commons / Polona. Its reading has not been checked by a Yiddish specialist.

## Ideas for next steps

- A shared queue of pages, so several people can check at once.
- Use a dictionary as well as the confidence score to decide what to flag.
- Ask a language model to suggest a fix for each doubtful word, for the person to accept or reject.
- Retrain the OCR on the saved corrections.
