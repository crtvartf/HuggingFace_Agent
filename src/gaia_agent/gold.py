"""Ground-truth answers from the gated GAIA validation set, for local scoring only.

GAIA asks that answers are not republished, so the cache lives in data/ (git-ignored).
Accept the dataset terms once at https://huggingface.co/datasets/gaia-benchmark/GAIA.
"""

import json

import pandas as pd
from huggingface_hub import hf_hub_download

from gaia_agent.settings import Settings

REPO = "gaia-benchmark/GAIA"
CANDIDATES = ("2023/validation/metadata.parquet", "2023/validation/metadata.jsonl")


def load_gold(settings: Settings) -> dict[str, str]:
    cache = settings.data_dir / "gold.json"
    if cache.exists():
        return json.loads(cache.read_text())
    settings.require("hf_token")
    token = settings.hf_token.get_secret_value()
    errors = []
    for filename in CANDIDATES:
        try:
            path = hf_hub_download(REPO, filename, repo_type="dataset", token=token)
        except Exception as e:
            errors.append(f"{filename}: {e}")
            continue
        df = pd.read_parquet(path) if filename.endswith(".parquet") else pd.read_json(path, lines=True)
        gold = dict(zip(df["task_id"], df["Final answer"].astype(str), strict=True))
        cache.write_text(json.dumps(gold))
        return gold
    raise SystemExit(
        "Could not download GAIA gold answers. Did you accept the dataset terms on Hugging Face?\n" + "\n".join(errors)
    )
