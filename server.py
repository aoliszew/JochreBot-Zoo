# Page Checker: a tiny custom tool for checking Yiddish OCR.
# Drop a page image in the browser; Jochre reads it; doubtful words are highlighted;
# a person confirms or fixes them; the confirmed page goes to an archive folder,
# and every fix is saved as a training example.
#
# Run:   python3 server.py      then open  http://localhost:8765
# Needs: Jochre 3 running on http://localhost:3434  (see ../jochre3/README.md)

import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
ARCHIVE = HERE / "archive"
SAMPLE = HERE / "sample" / "grodner-moment-1933-hias-notice.jpg"
NS = "{http://www.loc.gov/standards/alto/ns-v4#}"
WORK.mkdir(exist_ok=True)
ARCHIVE.mkdir(exist_ok=True)


def run_ocr(image_path):
    """Send the image to Jochre and turn its answer into a simple list of lines and words."""
    out = subprocess.run(["curl", "-s", "-X", "POST", "http://localhost:3434/ocr/file", "-F", "image=@" + str(image_path)],
                         capture_output=True, timeout=600)
    root = ET.fromstring(out.stdout)
    page = root.find(".//" + NS + "Page")
    lines = []
    for tl in root.iter(NS + "TextLine"):
        words = []
        for s in tl.findall(NS + "String"):
            roman = ""
            for alt in s.findall(NS + "ALTERNATIVE"):
                if alt.get("PURPOSE") == "Roman":
                    roman = alt.text or ""
            words.append(dict(x=int(float(s.get("HPOS"))), y=int(float(s.get("VPOS"))), w=int(float(s.get("WIDTH"))),
                              h=int(float(s.get("HEIGHT"))), text=s.get("CONTENT"), conf=float(s.get("WC") or 0), roman=roman))
        if words:
            lines.append(words)
    return dict(width=int(float(page.get("WIDTH"))), height=int(float(page.get("HEIGHT"))), lines=lines)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path, ctype):
        data = Path(path).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.path = self.path.split("?", 1)[0]  # ignore anything after "?"
        if self.path in ("/", "/index.html"):
            return self.send_file(HERE / "index.html", "text/html; charset=utf-8")
        if self.path.startswith("/image/"):
            name = Path(self.path.split("/image/", 1)[1]).name
            f = WORK / name
            if f.exists():
                return self.send_file(f, "image/png" if name.endswith(".png") else "image/jpeg")
        if self.path == "/archive-count":
            return self.send_json(dict(pages=len(list(ARCHIVE.glob("*.txt"))),
                                       fixes=sum(1 for _ in open(ARCHIVE / "corrections.jsonl")) if (ARCHIVE / "corrections.jsonl").exists() else 0))
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        try:
            if self.path in ("/ocr", "/sample"):
                page_id = time.strftime("page-%Y%m%d-%H%M%S")
                if self.path == "/sample":
                    # the request body may name a file in the sample/ folder; otherwise use the default sample
                    wanted = HERE / "sample" / Path(body.decode() or SAMPLE.name).name
                    name = page_id + ".jpg"
                    shutil.copy(wanted if wanted.exists() else SAMPLE, WORK / name)
                else:
                    ext = ".png" if (self.headers.get("X-Filename") or "").lower().endswith(".png") else ".jpg"
                    name = page_id + ext
                    (WORK / name).write_bytes(body)
                start = time.time()
                result = run_ocr(WORK / name)
                result.update(id=page_id, image=name, seconds=round(time.time() - start, 1))
                return self.send_json(result)
            if self.path == "/confirm":
                d = json.loads(body)
                page_id = Path(d["id"]).name
                stamp = time.strftime("%Y-%m-%d %H:%M")
                text = "\n".join(" ".join(w["text"] for w in line) for line in d["lines"])
                header = "# " + (d.get("title") or "Untitled page") + "\n# Checked by: " + (d.get("checker") or "anonymous") + ", " + stamp + "\n\n"
                (ARCHIVE / (page_id + ".txt")).write_text(header + text + "\n")
                (ARCHIVE / (page_id + ".json")).write_text(json.dumps(d, ensure_ascii=False, indent=1))
                src = WORK / Path(d["image"]).name
                if src.exists():
                    shutil.copy(src, ARCHIVE / src.name)
                fixes = 0
                with open(ARCHIVE / "corrections.jsonl", "a") as f:
                    for line in d["lines"]:
                        for w in line:
                            if w.get("status") == "fixed" and w["text"] != w.get("ocr"):
                                fixes += 1
                                f.write(json.dumps(dict(image=d["image"], box=[w["x"], w["y"], w["w"], w["h"]], ocr=w.get("ocr"),
                                                        human=w["text"], checker=d.get("checker"), time=stamp), ensure_ascii=False) + "\n")
                return self.send_json(dict(saved=page_id + ".txt", fixes=fixes, folder=str(ARCHIVE)))
        except Exception as e:  # show the problem in the browser instead of failing silently
            return self.send_json(dict(error=str(e)), 500)
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    print("Page Checker running: open http://localhost:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
