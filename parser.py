# TODO:
# Add a way to handle multiple verbs for one subject
# Make sure main verbs are identified for each clause 
# Clean up and make this my own
# Check singular/plural of output dicts for classifying each sentence


import os
import json
import csv
import subprocess
import sys
import spacy
import benepar


def load_model():
    # Download spaCy model if missing
    spacy_model = "en_core_web_md"
    try:
        nlp = spacy.load(spacy_model)
    except OSError:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", spacy_model])
        nlp = spacy.load(spacy_model)

    # Download Benepar model if missing
    benepar_model = "benepar_en3"
    download_dir = "./venv/nltk_data"
    os.makedirs(download_dir, exist_ok=True)
    try:
        benepar.download(benepar_model, download_dir=download_dir)
    except Exception:
        pass

    # Add Benepar to spaCy pipeline if missing
    if "benepar" not in nlp.pipe_names:
        nlp.add_pipe("benepar", config={"model": benepar_model})

    return nlp


def subjects_for_verb(verb):
    """Return a list of subjects (including coordinated) for a given verb token."""
    subjects = []
    for child in verb.children:
        if child.dep_ in ("nsubj", "nsubjpass", "csubj"):
            subjects.append(child.text)
            # Coordinated subjects (e.g., "Alice and Bob")
            subjects.extend([c.text for c in child.conjuncts])
    return subjects


def get_main_verb(verb):
    """Return auxiliary if present, otherwise return the main verb."""
    auxiliaries = [
        child.text
        for child in verb.children
        if child.dep_ in ("aux", "auxpass")
    ]
    if auxiliaries:
        # If multiple auxiliaries, return them joined
        return " ".join(auxiliaries)
    else:
        return verb.text


def parse_sentence(nlp, sentence):
    doc = nlp(sentence)
    results = []

    for sent in doc.sents:
        verb_subject_map = {}

        for verb in sent:
            if verb.pos_ == "VERB" and verb.dep_ == "ROOT":
                subjects = subjects_for_verb(verb)
                if subjects:
                    main_verb = get_main_verb(verb)
                    verb_subject_map[main_verb] = subjects

        results.append({
            "sentence": sentence,
            "verb_subject_map": verb_subject_map,
        })

    return results


def parse_json_file(nlp, json_file, output_csv):
    """Parse all sentences in a JSON file and save results to CSV."""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_results = []

    for entry in data:
        sentence = entry["sentence"]
        label = entry.get("label", "")
        sentence_results = parse_sentence(nlp, sentence)
        for res in sentence_results:
            res["label"] = label
            # Convert verb-subject mapping to a string for CSV
            res["verb_subject_map"] = "; ".join(
                [f"{v}: {', '.join(subjs)}" for v, subjs in res["verb_subject_map"].items()]
            )
            all_results.append(res)

    # Save CSV
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sentence", "label", "verb_subject_map"])
        writer.writeheader()
        for row in all_results:
            writer.writerow(row)

    print(f"✅ Done! Results saved to '{output_csv}'")


if __name__ == "__main__":
    nlp = load_model()
    parse_json_file(nlp, "./data/test_sva_data.json", "parsed_results.csv")
