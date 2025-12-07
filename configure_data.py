import copy
import re
import random
import csv
import json
import inflect
from wonderwords import RandomWord
import language_tool_python
from language_tool_python.utils import classify_matches, TextStatus


# Word generation 
rw = RandomWord()
# Grammatical number (singular/plural) changing
ie = inflect.engine()
# Filtering the 'correct' (grammatically) real sentences
lt = language_tool_python.LanguageTool("en-US")


# Writes to a JSON file the sentences from a text file that are over 35 words long (complex) and are likely to be grammatically correct
# They are all written with label 1  
def filter_real_sentences(filename):
    real_sentences = []

    with open(filename, "r", encoding="utf-8") as fp:
        data = fp.read()

    # Delete newlines so each sentence can be put on its own line later
    data = data.replace("\n", " ")

    # Get the sentences
    sentences = re.split(r'[.!?]', data)

    # Iterate over each sentence
    for sentence in sentences:
        sentence = sentence.strip()

        # Keep sentences that are over 35 words long and are likely to be grammatically correct
        if len(sentence.split()) > 35:
            matches = lt.check(sentence)
            status = classify_matches(matches)
            if status == TextStatus.CORRECT:
                sentence = sentence.replace('"', "'")
                real_sentences.append({"sentence": sentence, "label": 1})  # all have label 1

    # Write to JSON file
    with open("./data/real_sentences.json", "w", encoding="utf-8") as fp:
        json.dump(real_sentences, fp, indent=4)


# Writes to a CSV file the subject-verb agreement errored sentences from m2 files (the last annotation to be made for each sentence will always be SVA)
# Finds the incorrect SVA sentences and writes them with label 0
# For each incorrect SVA sentence, makes the given annotations to get the correct SVA sentence; writes with label 1
# Returns the average count of how many sentence pairs were extracted from the files
def extract_sva_sentence_pairs(file_list):
    # Keep track of total sentence pairs extracted
    total_count = 0

    # All output goes to one file
    with open("./data/extracted_sentences.csv", "w", encoding="utf-8") as out_fp:
        for file in file_list:
            # Keep track of sentences pairs extracted per file
            file_count = 0

            with open(file, "r", encoding="utf-8") as fp:
                lines = fp.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Find the original errored sentence
                if line.startswith("S "):
                    original_sentence = line[2:]  # remove "S "
                    annotations = []
                    j = i + 1

                    # Collect annotation lines immediately after the current sentence
                    while j < len(lines) and lines[j].startswith("A"):
                        annotations.append(lines[j])
                        j += 1

                    if annotations:
                        # The following section was adapted from an algorithm (from the corpus) that applies the annotations in an m2 file
                        tokens = original_sentence.split()
                        incorrect_tokens = copy.deepcopy(tokens)
                        offset = 0

                        for a in annotations[:-1]:  # ignore the last annotation (SVA)
                            parts = a.split("|||")
                            span_raw = parts[0].split()
                            start = int(span_raw[1])
                            end = int(span_raw[2])

                            replacement_tokens = parts[2].split()

                            # Apply edit with offset compensation
                            incorrect_tokens[start + offset : end + offset] = replacement_tokens

                            # Update offset
                            offset = offset - (end - start) + len(replacement_tokens)

                        incorrect_sentence = " ".join(incorrect_tokens)

                        # Apply the last edit (SVA) to produce the "correct" sentence
                        last = annotations[-1].split("|||")
                        span_raw = last[0].split()
                        start = int(span_raw[1])
                        end = int(span_raw[2])
                        replacement_tokens = last[2].split()
                        correct_tokens = incorrect_tokens.copy()
                        correct_tokens[start : end] = replacement_tokens
                        correct_sentence = " ".join(correct_tokens)

                        # Write to CSV
                        incorrect_sentence = incorrect_sentence.replace('"', "'")
                        correct_sentence = correct_sentence.replace('"', "'")
                        out_fp.write(f'"{incorrect_sentence}",0\n')
                        out_fp.write(f'"{correct_sentence}",1\n')

                        file_count += 1

                    # Skip to the next sentence
                    i = j

                else:
                    i += 1

            total_count += file_count

    # Return the average number of pairs extracted
    return total_count / len(file_list)


# Returns the singular and plural forms of a random noun
def get_noun():
    noun_s = rw.word(include_parts_of_speech=["noun"]) 
    noun_p = ie.plural(noun_s)
    return noun_s.strip().lower(), noun_p.strip().lower()


# Returns the singular and plural forms of a random verb
def get_verb():
    verb_p = rw.word(include_parts_of_speech=["verb"])
    verb_s = ie.plural(verb_p)
    return verb_s.strip().lower(), verb_p.strip().lower()


# Returns a random adjective or no adjective
def get_adj():
    if random.random() < 0.4:
        return rw.word(include_parts_of_speech=["adjective"]).strip().lower() 
    return ""


# Returns a random adverb or no adverb
def get_adv():
    if random.random() < 0.4:
        adverbs = [
            "quickly", "slowly", "silently", "loudly", "sadly", "happily",
            "gracefully", "barely", "rarely", "often", "always", "never",
            "sometimes", "suddenly", "eagerly", "quietly"
        ]
        return random.choice(adverbs)
    return ""


# Returns "the" followed by a noun and possibly an adjective before the noun
# Return two of these phrases joined by "and" if two_nouns is True
def build_noun_phrase(plural=False, two_nouns=False):
    noun1_s, noun1_p = get_noun()
    adj1 = get_adj()

    if not two_nouns:
        if plural:
            return f"the {adj1 + " " if adj1 else ""}{noun1_p}"
        return f"the {adj1 + " " if adj1 else ""}{noun1_s}"
        
    noun2_s, noun2_p = get_noun()
    adj2 = get_adj()
    
    noun1 = noun1_p if plural else noun1_s
    noun2 = noun2_p if plural else noun2_s

    phrase1 = f"the {adj1 + " " if adj1 else ""}{noun1}"
    phrase2 = f"the {adj2 + " " if adj2 else ""}{noun2}"

    return f"{phrase1} and {phrase2}"


# Returns a preposition followed by a noun phrase
def build_prepositional_phrase():
    preps = [
        "in", "on", "under", "beside", "near", "around", "behind", "inside" "on top of", 
        "of", "over", "at", "to", "next to", "by", "onto", "into", "up to"
        ]
    np = build_noun_phrase(random.choice([True, False]), random.choice([True, False]))

    return f"{random.choice(preps)} {np}"


# Returns "that" followed by a verb and a maybe a noun phrase
def build_relative_clause(plural=False):
    verb_s, verb_p = get_verb()

    obj = ""
    include_obj = random.random() < 0.5
    if include_obj:
        obj = build_noun_phrase(random.choice([True, False]), random.choice([True, False])) 

    verb = verb_s
    if plural:
        verb = verb_p

    return f"that {verb}{" " + obj if obj else ""}"


# Returns a connector word followed by "the", a noun, and a verb
def build_subordinate_clause():
    connectors = [
        "because", "when", "although", "after", "before", "since"
    ]   
    connector = random.choice(connectors)

    noun_s, noun_p = get_noun()
    verb_s, verb_p = get_verb()
    subj = noun_s
    verb = verb_s
    
    plural = random.random() < 0.5
    if plural:
        subj = noun_p
        verb = verb_p

    return f"{connector} the {subj} {verb}"


# Returns a grammatically correct sentence (in terms of parts of speech)
# The sentence is tokenized (both words and punctuation characters are tokens) 
def build_sentence(subj, verb, obj=None, adv=None, pp=None, rel=None, sub=None, local_seed=None):
    # Use a seed so the sentence can be replicated
    random.seed(local_seed)

    parts = []

    # Subordinate clause might be first
    if sub and random.random() < 0.4:
        parts.append(f"{sub} ,")  # the comma is its own token

    # Subject (determinant and noun)
    parts.append(subj)

    # Relative clause goes after the subject because it has the same grammatical number as the subject (keeping things simple)
    if rel:
        parts.append(rel)

    # Adverb might go before verb
    if adv and random.random() < 0.5:
        parts.append(adv)

    # Verb
    parts.append(verb)

    # Adverb goes after verb if not used yet
    if adv and adv not in parts:
        parts.append(adv)

    # Object
    if obj:
        parts.append(obj)

    # Prepositional phrase
    if pp:
        parts.append(pp)

    # Subordinate clause if not used yet
    if sub and not any(p.startswith(sub) for p in parts):
        parts.append(sub)

    # Final formatting
    sentence = " ".join(parts)
    sentence = sentence[0].upper() + sentence[1:]
    
    return sentence + " ."  # the period is its own token


# Uses randomness to return two sentences
# One sentence has an SVA error; the other sentence is exactly the same, but with the error fixed
def generate_sva_sentence_pair(): 
    # Decide if the subject will be plural
    plural_subj = random.random() < 0.5
    # Decide if there will be two subjects
    two_subj = random.random() < 0.3
    # Get a random subject
    subj = build_noun_phrase(plural_subj, two_subj)

    # Get the correct and incorrect versions of the same random verb (different grammatical numbers) 
    verb_s, verb_p = get_verb()
    correct_verb = verb_p if plural_subj else verb_s
    incorrect_verb = verb_s if plural_subj else verb_p

    # If there are two subjects, the correct verb will be plural
    if two_subj:
        correct_verb = verb_p
        incorrect_verb = verb_s 
        plural_subj = True  # Still keep track of the grammatical number of the subject so the relative clause describing the subject will match

    # Get a random adverb
    adv = get_adv()

    # Decide if there will be a random object
    include_object = random.random() < 0.75
    obj = ""
    if include_object:
        obj = build_noun_phrase(plural=random.choice([True, False]), two_nouns=random.random() < 0.25)

    # Decide if there will be a random prepositional phrase
    include_pp = random.random() < 0.5
    pp = build_prepositional_phrase() if include_pp else ""

    # Decide if there will be a random relative clause that describes the subject
    include_rel = random.random() < 0.4
    rel = build_relative_clause(plural=plural_subj) if include_rel else ""

    # Decide if there will be a random subordinate clause
    include_sub = random.random() < 0.4
    sub = build_subordinate_clause() if include_sub else ""

    # Generate a random local seed so a sentence can be replicated
    local_seed = random.randint(0, 2**32 - 1)

    # Build the sentence pairs
    # The difference between the two is only the grammatical number of the verb
    correct = build_sentence(subj, correct_verb, obj, adv, pp, rel, sub, local_seed)
    incorrect = build_sentence(subj, incorrect_verb, obj, adv, pp, rel, sub, local_seed)

    return correct, incorrect


# Writes to a CSV file n pairs of randomly generated SVA sentences (each sentence is the same except for the SVA error) 
# Incorrect SVA sentences are labeled 0
# Correct SVA sentences are labeled 1
def generate_sva_sentence_pairs(n):
    with open("./data/generated_sentences.csv", "w", encoding="utf-8") as fp:
        for i in range(n):
            correct, incorrect = generate_sva_sentence_pair()
            fp.write(f'"{incorrect}",{0}\n')
            fp.write(f'"{correct}",{1}\n')


# Shuffles and combines the data from the extracted and generated SVA sentence CSV files into three JSON files
# One JSON file is for training: contains 1/2 of the sentence pairs 
# One JSON file is for validating: contains one sentence from each pair of another 1/4 of the sentence pairs 
# One JSON file is for testing: contains one sentence from each pair of the last 1/4 of the sentence pairs
# The final distribution of kept data: train: 2/3, validation: 1/6, test: 1/6
def csv_to_json():
    # Combine the data into one list
    all_sentences = []
    for file in ["./data/extracted_sentences.csv", "./data/generated_sentences.csv"]:
        with open(file, "r", encoding="utf-8") as fp:
            reader = csv.reader(fp)
            all_sentences.extend([row for row in reader])

    # Keep track of sentence pairs
    pairs = []
    for i in range(0, len(all_sentences), 2):
        s1, l1 = all_sentences[i]
        s2, l2 = all_sentences[i + 1]
        pairs.append([{"sentence": s1, "label": int(l1)}, {"sentence": s2, "label": int(l2)}])

    # Shuffle the pairs
    random.shuffle(pairs)

    # Randomize the order of the sentences in each pair
    for pair in pairs:
        if random.random() < 0.5:
            pair[0], pair[1] = pair[1], pair[0]

    # Split into train (half of pairs)
    n = len(pairs)
    train_end = n // 2
    train_pairs = pairs[:train_end]
    remaining_pairs = pairs[train_end:]

    # From the remaining pairs, take one sentence from each pair for validation and test
    remaining_sentences = []
    for pair in remaining_pairs:
        remaining_sentences.append(random.choice(pair))
    random.shuffle(remaining_sentences)
    valid_end = len(remaining_sentences) // 2
    valid_sentences = remaining_sentences[:valid_end]
    test_sentences = remaining_sentences[valid_end:]

    # Flatten train pairs (keep both sentences in each training pair)
    train_sentences = []
    for pair in train_pairs:
        for sentence in pair:
            train_sentences.append(sentence)
    
    # Write data to JSON files
    with open("./data/train_sva_data.json", "w", encoding="utf-8") as fp:
        json.dump(train_sentences, fp, indent=4)

    with open("./data/valid_sva_data.json", "w", encoding="utf-8") as fp:
        json.dump(valid_sentences, fp, indent=4)

    with open("./data/test_sva_data.json", "w", encoding="utf-8") as fp:
        json.dump(test_sentences, fp, indent=4)


# Extracts the SVA sentence pairs from the given m2 files (written to a CSV file)
# Generates random SVA sentence pairs (written to a CSV file); the number of generated pairs equals the average number of extracted pairs from the m2 files
# Combines the two CSV files into json files for training, validating, and testing
def configure_data():
    # SVA error and annotation corpus
    m2_files = ["./data/fce.m2", "./data/lang8.m2", "./data/nucle.m2", "./data/wi_locness.m2"]

    # Extract the correct and incorrect sentences from the corpus and record the average number of pairs for each file
    pair_avg = extract_sva_sentence_pairs(m2_files)

    # Generate pair_avg synthetic pairs of correct and incorrect SVA sentences
    generate_sva_sentence_pairs(int(pair_avg))

    # Convert outputs from previous functions to shuffled train, validate, and test JSON files
    csv_to_json()

    # Create one last test JSON file with complex real-world sentences (all labeled 1) 
    filter_real_sentences("./data/pg8448.txt")


configure_data()
