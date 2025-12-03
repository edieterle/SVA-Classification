import random
import inflect
from wonderwords import RandomWord


rw = RandomWord()
ie = inflect.engine()


# Writes to a csv file the subject-verb agreement errored sentences from a m2-foratted file
# Finds the incorrect SVA sentences and writes them with label "I"
# For each incorrect SVA sentence, makes the given annotations to get the correct SVA sentence; writes with label "C"
def extract_sva_sentence_pairs(filename):
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

                # Write the incorrect version of the sentence
                fp.write(f"'{incorrect}',I\n")

                # Use the annotaton to get the correct version of the sentence
                parts = annotations[0].split("|||")
                start = int(parts[0].split()[1])
                end = int(parts[0].split()[2])
                replacement = parts[2]
                tokens = incorrect.split()
                correct = tokens[:start] + [replacement] + tokens[end:]
                correct = " ".join(correct)

                # Write the correct version of the sentence
                fp.write(f"'{correct}',C\n")
                
            # Skip to the next sentence
            i = j 

        else:
            i += 1

    fp.close()


def get_noun():
    noun_s = rw.word(include_parts_of_speech=["noun"]) 
    noun_p = ie.plural(noun_s)
    return noun_s, noun_p


def get_verb():
    verb_p = rw.word(include_parts_of_speech=["verb"])
    verb_s = ie.plural(verb_p)
    return verb_s, verb_p


def get_adj():
    if random.random() < 0.4:
        return rw.word(include_parts_of_speech=["adjective"]) 
    return ""


def get_adv():
    if random.random() < 0.4:
        adverbs = [
            "quickly", "slowly", "silently", "loudly", "sadly", "happily",
            "gracefully", "barely", "rarely", "often", "always", "never",
            "sometimes", "suddenly", "eagerly", "quietly"
        ]
        return random.choice(adverbs)
    return ""


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


def build_prepositional_phrase():
    preps = [
        "in", "on", "under", "beside", "near", "around", "behind", "inside"
        "on top of", "of", "over", "at", "to", "next to", "by", "onto", "into",
        "up to"
        ]
    np = build_noun_phrase(random.choice([True, False]), random.choice([True, False]))
    return f"{random.choice(preps)} {np}"


def build_relative_clause(plural=False):
    verb_s, verb_p = get_verb()
    noun_s, noun_p = get_noun()
    adj = get_adj()
    obj = f"the {adj + " " if adj else ""}{random.choice([noun_s, noun_p])}" 

    verb = verb_s
    if plural:
        verb = verb_p

    return f"that {verb} {obj}"


def build_subordinate_clause():
    connectors = [
        "because", "when", "although", "after", 
        "before", "since", "but", "and"
    ]   
    connector = random.choice(connectors)

    noun_s, noun_p = get_noun()
    verb_s, verb_p = get_verb()
    subj = noun_s
    verb = verb_s
    
    plural = random.choice([True, False])
    if plural:
        subj = noun_p
        verb = verb_p

    return f"{connector} {subj} {verb}"


def build_sentence(subject, verb, obj=None, adv=None, pp=None, rel=None, sub=None, seed=None):
    if seed is not None:
        random.seed(seed)

    parts = []

    parts.append(subject)

    if adv:
        if random.random() < 0.5:
            parts.append(adv)

    parts.append(verb)

    if adv and adv not in parts:
        parts.append(adv)

    if obj:
        parts.append(obj)

    if pp:
        if random.random() < 0.3:
            parts.insert(1, pp)
        else:
            parts.append(pp)

    if rel:
        parts.append(rel)

    if sub:
        if random.random() < 0.4:
            parts.insert(0, f"{sub},")
        else:
            parts.append(sub)

    return " ".join(parts).capitalize() + "."


def generate_sva_sentence_pair(): 
    plural_subj = random.choice([True, False])
    two_nouns = random.random() < 0.3
    subj = build_noun_phrase(plural_subj, two_nouns)

    verb_s, verb_p = get_verb()
    correct_verb = verb_p if plural_subj else verb_s
    incorrect_verb = verb_s if plural_subj else verb_p

    if two_nouns:
        correct_verb = verb_s
        incorrect_verb = verb_p

    adv = get_adv()

    include_object = random.random() < 0.75
    obj = ""
    if include_object:
        obj = build_noun_phrase(plural=random.choice([True, False]), two_nouns=random.random() < 0.25)

    include_pp = random.random() < 0.5
    pp = build_prepositional_phrase() if include_pp else ""

    include_rel = random.random() < 0.35
    rel = build_relative_clause(plural=random.choice([True, False])) if include_rel else ""

    include_sub = random.random() < 0.35
    sub = build_subordinate_clause() if include_sub else ""

    seed = random.randint(0, 2**32 - 1)

    correct_sentence = build_sentence(subj, correct_verb, obj, adv, pp, rel, sub, seed)
    incorrect_sentence = build_sentence(subj, incorrect_verb, obj, adv, pp, rel, sub, seed)

    return correct_sentence, incorrect_sentence


def generate_sva_sentence_pairs(n):
    with open(f"generated_sentences.csv", "w", encoding="utf-8") as fp:
        for i in range(n):
            correct, incorrect = generate_sva_sentence_pair()
            fp.write(f"'{incorrect}',I\n")
            fp.write(f"'{correct}',C\n")


def main(filename, n):
    extract_sva_sentence_pairs(filename)
    generate_sva_sentence_pairs(n)


if __name__ == "__main__":
    main("annotations.m2", 7183)
