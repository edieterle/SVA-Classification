print("This may take a while...")
print()

print("Preparing dependencies...")
from pathlib import Path
from configure_data import configure_data
from fine_tune_llm import create_llm, test_created_llm
from parser import create_parser, test_created_parser
print("Dependencies ready!")
print()


def main():
    configured_data = [
        "./data/test_real_sentences.json", "./data/test_sva_data.json", 
        "./data/train_sva_data.json", "./data/valid_sva_data.json"
        ]
    all_exist = True
    for file in configured_data:
        file = Path(file)
        if not file.exists():
            all_exist = False
    # Configure the data if it has not been configured yet
    if not all_exist:
        print("Configuring data...")
        configure_data()
        print("Data ready!")
    else:
        print("Data already configured!")

    print()

    created_llm = [
        "./llm/best_llm/config.json", "./llm/best_llm/model.safetensors",
        "./llm/best_llm/training_args.bin"
    ]
    all_exist = True
    for file in created_llm:
        file = Path(file)
        if not file.exists():
            all_exist = False
    model_dir = "./llm/best_llm"
    # Fine-tune the LLM if it has not been fine-tuned yet
    if not all_exist:
        print("Fine-tuning LLM...")
        model_dir = create_llm()
        print("LLM ready!")
    else:
        print("LLM already fine-tuned!")

    print()

    print("Loading parser...")
    nlp = create_parser()
    print("Parser ready!")

    print()

    print("Testing LLM...")
    results_llm = test_created_llm(model_dir)
    accuracy_llm = results_llm[0]
    accuracy_llm_real_world = results_llm[1]
    print("Done!")

    print()

    print("Testing parser...")
    results_parser = test_created_parser(nlp)
    [accuracy_parser, not_parsed] = results_parser[0]
    [accuracy_parser_real_world, not_parsed_real_world] = results_parser[1]
    print("Done!")

    print()

    print(f"Results:")
    print(f"  Extracted/Generated:")
    print(f"    LLM:               {accuracy_llm}")
    print(f"    Parser:            {accuracy_parser}")
    print(f"      Couldn't parse:  {not_parsed}")
    print(f"  Real-World:")
    print(f"    LLM:               {accuracy_llm_real_world}")
    print(f"    Parser:            {accuracy_parser_real_world}")
    print(f"      Couldn't parse:  {not_parsed_real_world}")
    

if __name__ == "__main__":
    main()
