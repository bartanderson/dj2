from pathlib import Path
import yaml


def load_analysis_profiles(path: str = "tools/analysis/analysis_profiles.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profiles = data["profiles"]
    exclude = set(data.get("exclude", []))

    return profiles, exclude

def build_profile_prefixes(include_paths: list[str]) -> list[str]:
    prefixes = []

    for p in include_paths:
        p = p.strip().replace("/", ".").replace("\\", ".")

        if not p.endswith("."):
            p += "."

        prefixes.append(p)

    return prefixes