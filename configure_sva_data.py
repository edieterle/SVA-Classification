import random
import csv
import json
import inflect
from wonderwords import RandomWord


# Used for word generation and grammatical number (singular/plural) changing
rw = RandomWord()
ie = inflect.engine()


# Writes to a csv file the subject-verb agreement errored sentences from a m2-foratted file
# Finds the incorrect SVA sentences and writes them with label "I"
# For each incorrect SVA sentence, makes the given annotations to get the correct SVA sentence; writes with label "C"
# Returns a count of how many sentence pairs were extracted
def extract_sva_sentence_pairs(filename):
    count = 0

    with open(filename, "r", encoding="utf-8") as fp:
        lines = []
        for line in fp:
            line = line.strip()
            lines.append(line)

    fp = open("extracted_sentences.csv", "w", encoding="utf-8")

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("S"):
            incorrect = line[2:]  # remove "S " prefix
            annotations = []
            j = i + 1

            # Collect annotation lines immediately after the current sentence
            while j < len(lines) and lines[j].startswith("A"):
                annotations.append(lines[j])
                j += 1

            # Keep sentences with exactly one annotation and it is SVA
            if len(annotations) == 1 and "R:VERB:SVA" in annotations[0]:
                # Keep track of how many sentence pairs are extracted
                count += 1

                # Write the incorrect version of the sentence
                fp.write(f'"{incorrect}",I\n')

                # Use the annotaton to get the correct version of the sentence
                parts = annotations[0].split("|||")
                start = int(parts[0].split()[1])
                end = int(parts[0].split()[2])
                replacement = parts[2]
                tokens = incorrect.split()
                correct = tokens[:start] + [replacement] + tokens[end:]
                correct = " ".join(correct)

                # Write the correct version of the sentence
                fp.write(f'"{correct}",C\n')
                
            # Skip to the next sentence
            i = j 

        else:
            i += 1

    fp.close()
    return count


# Returns the singular and plural forms of a random noun
def get_noun():
    noun_s = rw.word(include_parts_of_speech=["noun"]) 
    noun_p = ie.plural(noun_s)
    return noun_s, noun_p


# Returns the singular and plural forms of a random verb
def get_verb():
    verb_p = rw.word(include_parts_of_speech=["verb"])
    verb_s = ie.plural(verb_p)
    return verb_s, verb_p


# Returns a random adjective or no adjective
def get_adj():
    if random.random() < 0.4:
        return rw.word(include_parts_of_speech=["adjective"]) 
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

    return f"that {verb + " " if obj else ""}{obj}"


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


# Returns a grammatically correct, tokenized sentence (punctuation is split into separate words) 
def build_sentence(subj, verb, obj=None, adv=None, pp=None, rel=None, sub=None, seed=None):
    # Use a seed to control where the different parts of the sentence go
    if seed is not None:
        random.seed(seed)

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

    # Generate a random seed so a sentence can be replicated
    seed = random.randint(0, 2**32 - 1)

    # Build the sentence pairs
    # The difference between the two is only the grammatical number of the verb
    correct = build_sentence(subj, correct_verb, obj, adv, pp, rel, sub, seed)
    incorrect = build_sentence(subj, incorrect_verb, obj, adv, pp, rel, sub, seed)

    return correct, incorrect


# Writes to a csv file n pairs of randomly generated SVA sentences (each sentence is the same except for the SVA error) 
# Incorrect SVA sentences are labeled "I"
# Correct SVA sentences are labeled "C"
def generate_sva_sentence_pairs(n):
    with open(f"generated_sentences.csv", "w", encoding="utf-8") as fp:
        for i in range(n):
            correct, incorrect = generate_sva_sentence_pair()
            fp.write(f'"{incorrect}",I\n')
            fp.write(f'"{correct}",C\n')


# Combines the data from both the extracted and the generated SVA sentence csv files into one json file
def combine_extracted_generated_csv_to_json(file1="extracted_sentences.csv", file2="generated_sentences.csv"):
    data = []

    for file in [file1, file2]:
        with open(file, "r", encoding="utf-8") as fp:
            reader = csv.reader(fp, delimiter=",", quotechar='"')
            for row in reader:
                sentence, label = row
                data.append({
                    "sentence": sentence,
                    "label": label
                })

    with open("test_data.json", "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=4)


# Extracts the sva sentence pairs from the given m2 file (written to a csv file)
# Generates random sva sentence pairs (written to a csv file); the number of generated pairs equals the number of extracted pairs
# Combines the two csv files into one json file 
def configure_sva_data(filename):
    n_pairs = extract_sva_sentence_pairs(filename)
    generate_sva_sentence_pairs(n_pairs)
    combine_extracted_generated_csv_to_json()


if __name__ == "__main__":
    configure_sva_data("annotations.m2")
