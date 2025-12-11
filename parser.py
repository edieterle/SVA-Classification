from collections import defaultdict
import os
import json
import subprocess
import sys
import spacy
import lemminflect
import benepar
import inflect


# Loads model for classification
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


# Return a list of subjects (including coordinated) for a verb
def subjects_for_verb(verb):
    subjects = []

    # Traverse all descendants of the verb to find subjects
    for desc in verb.subtree:
        if desc.dep_ in ("nsubj", "nsubjpass", "csubj"):
            subjects.append(desc.text)
            subjects.extend([c.text for c in desc.conjuncts])

    # Deduplicate
    return list(set(subjects))


# Extracts auxiliaries (or main verbs if no auxiliaries) and their corresponding subjects
# Allows multiple occurrences of the same verb with different subjects
def parse_sentence(nlp, sentence):
    doc = nlp(sentence)
    results = []

    for sent in doc.sents:
        verb_subject_map = defaultdict(list)  # key: verb/aux, value: list of subject lists
        verbs = [token for token in sent if token.pos_ == "VERB"]
        for verb in verbs:
            subjects = subjects_for_verb(verb)
            if subjects:
                auxs = [child.text for child in verb.children if child.dep_ in ("aux", "auxpass")]
                if auxs:
                    for aux in auxs:
                        verb_subject_map[aux].append(subjects)
                else:
                    verb_subject_map[verb.text].append(subjects)

        # Convert defaultdict to normal dict for output
        results.append({"sentence": sentence, "verb_subject_map": dict(verb_subject_map)})

    return results



# Predicts subject-verb agreement in a given sentence mapping
# Returns 1 if the sentence is good, 0 if there is an SVA error, or -1 if the sentence could not be parsed (empty mapping input)
def predict_sva(nlp, verb_subject_map):
    ie = inflect.engine()

    # The sentence could not be parsed
    if not verb_subject_map:
        return -1 

    for verb, subject_lists in verb_subject_map.items():
        for subjects in subject_lists:
            # Get grammatical number of the verb
            singular_verb = False

            doc = nlp(verb)
            token = doc[0]  # verb

            # Detect tense
            morph = token.morph
            is_past = "Tense=Past" in morph
            is_present = "Tense=Pres" in morph

            if is_present:
                third_sg = token._.inflect("VBZ")
                if verb == third_sg:
                    singular_verb = True
            elif is_past:
                # Past form is the same for all persons
                past = token._.inflect("VBD")
                if verb == past:
                    singular_verb = True

            # Get grammatical number of the subjects
            singular_subject = False
            
            if len(subjects) == 1:  # if there are more than one coordinated nouns, then the subject is plural
                subj = subjects[0]
                if ie.singular_noun(subj) == False:
                    singular_subject = True

            # The grammatical number of the verb and one of the subjects does not match: SVA error
            if singular_verb != singular_subject:
                return 0

    # No SVA errors found
    return 1 


# Calculates accuracy from the given ground truth and predicted labels
# Also returns the distribution of sentences that could not be parsed
def get_accuracy(list_gt, list_pred):
    total_predictions = 0
    correct_predictions = 0
    no_predictions = 0

    for i in range(len(list_pred)):
        if list_pred[i] == -1:
            no_predictions += 1
        else:
            total_predictions += 1
        if list_pred[i] == list_gt[i]:
            correct_predictions += 1

    accuracy = correct_predictions / total_predictions
    not_parsed = no_predictions / total_predictions

    return accuracy, not_parsed 


# Tests the model
def test(nlp, json_file):
    with open(json_file, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    list_gt = []
    list_pred = []

    for entry in data:
        sentence = entry["sentence"]
        label = entry.get("label", "")

        # Parse the sentence to get verb_subject_map
        sentence_results = parse_sentence(nlp, sentence)

        # Combine all verb_subject_maps in case there are multiple sentences returned
        verb_subject_map = defaultdict(list)
        for res in sentence_results:
            for verb, subject_lists in res["verb_subject_map"].items():
                verb_subject_map[verb].extend(subject_lists)

        # Predict SVA using the verb_subject_map
        prediction = predict_sva(nlp, dict(verb_subject_map))

        list_gt.append(label)
        list_pred.append(prediction)

    return get_accuracy(list_gt, list_pred)


# Creates a parser model for SVA classification
def create_parser():
    nlp = load_model()
    return nlp


# Tests the created parser model on the testing data from the extracted and generated SVA sentences
# Also separately tests on the complex, real-world sentences
def test_created_parser(nlp):
    test_accuracies = []
    for file in ["./data/test_sva_data.json", "./data/test_real_data.json"]:
        test_accuracy, not_parsed = test(nlp, file)
        test_accuracies.append([round(test_accuracy, 3), round(not_parsed, 3)])
    return test_accuracies
