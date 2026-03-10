import pandas as pd
import json

INPUT_FILE = "ddq_document_v2.xlsx"
OUTPUT_FILE = "ddq_document_v2.json"


def clean_multiline(text):
    
    if pd.isna(text):
        return []

    lines = str(text).split("\n")
    return [l.strip().strip(",") for l in lines if l.strip()]


def clean_keywords(text):
    
    if pd.isna(text):
        return []

    return [k.strip() for k in str(text).split(",") if k.strip()]


def main():
    df = pd.read_excel(INPUT_FILE)

    intents = []

    for _, row in df.iterrows():

        intent = {
            "document": str(row["document"]).strip(),
            "description": str(row["description"]).strip(),
            "examples": clean_multiline(row["examples"]),
            "keywords": clean_keywords(row["keyword"]),
            "metadata": str(row["metadata"]).strip()
        }

        intents.append(intent)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(intents, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(intents)} intents -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()