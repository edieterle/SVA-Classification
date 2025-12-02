import inflect
from wonderwords import RandomWord


# Writes to a csv file the subject-verb agreement errored sentences from a m2-foratted file
# Finds the incorrect SVA sentences and writes them with label "I"
# For each incorrect SVA sentence, makes the given annotations to get the correct SVA sentence; writes with label "C"
def extract_sva_sentences(filename):
    sva_sentences = []
    labels = []

    with open(filename, "r", encoding="utf-8") as fp:
        lines = []
        for line in fp:
            line = line.strip()
            lines.append(line)

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("S"):
            original_sentence = line[2:]  # remove "S " prefix
            annotations = []
            j = i + 1

            # Collect annotation lines immediately after the current sentence
            while j < len(lines) and lines[j].startswith("A"):
                annotations.append(lines[j])
                j += 1

            # Keep sentences with exactly one annotation and it is SVA
            if len(annotations) == 1 and "R:VERB:SVA" in annotations[0]:

                # Store the incorrect version of the sentence
                sva_sentences.append(original_sentence)
                labels.append("I")

                # Use the annotaton to get the correct version of the sentence
                parts = annotations[0].split("|||")
                start = int(parts[0].split()[1])
                end = int(parts[0].split()[2])
                replacement = parts[2]
                tokens = original_sentence.split()
                corrected_sentence = tokens[:start] + [replacement] + tokens[end:]
                corrected_sentence = " ".join(corrected_sentence)

                # Store the correct version of the sentence
                sva_sentences.append(corrected_sentence)
                labels.append("C")
                
            # Skip to the next sentence
            i = j 

        else:
            i += 1

    # Write sentences to a new file
    with open(f"extracted_sentences.csv", "w", encoding="utf-8") as fp:
        for i in range(len(labels)):
            fp.write(f"'{sva_sentences[i]}',{labels[i]}\n")


def create_sva_sentences(n):
    rw = RandomWord()
    ie = inflect.engine()

    for i in range(n):
        noun_s = rw.word(include_parts_of_speech=["noun"]) 
        noun_p = ie.plural(noun_s)
        verb_p = rw.word(include_parts_of_speech=["verb"])
        verb_s = ie.plural(verb_p) 


        # <a, an, _, the> <adj, _> snoun <', modifying phrase?,', prep phrase, _> <adv, _> pverb <obj, > <adv, _>   I

        # <a, an, _, the> <adj, _> pnoun sverb <obj, > <adv, _>   I
        # <a, an, _, the> <adj, _> snoun sverb <obj, > <adv, _>   C
        # <a, an, _, the> <adj, _> pnoun pverb <obj, > <adv, _>   C
        # <a, an, _, the> <adj, _> <snoun, pnoun> and <a, an, _, the> <adj, > <snoun, pnoun> sverb <adv, _>  I  
        # <a, an, _, the> <adj, _> <snoun, pnoun> and <a, an, _, the> <adj, > <snoun, pnoun> pverb <adv, _>  C
        # <a, an, _, the> <adj, _> 
    
create_sva_sentences()

