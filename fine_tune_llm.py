# TODO:
# Retrain once configure_data is ready


import json
import os
import numpy as np
import pandas as pd
import polars as pl
import torch
from datasets import Dataset, DatasetDict
from transformers import (AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer)


# Loads model and tokenizer for classification
def load_model_and_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
    return tokenizer, model


# Tokenizes the sentence column
def tokenize_function(tokenizer, examples):
    return tokenizer(examples["sentence"], padding="max_length", truncation=True)


# Combines training and validation Pandas DataFrames into a single HuggingFace DatasetDict
def convert_df_to_dataset(df_train, df_valid):
    # Convert each DataFrame to a HuggingFace Dataset
    train_ds = Dataset.from_pandas(df_train)
    valid_ds = Dataset.from_pandas(df_valid)
    
    # Combine them into a single DatasetDict
    dataset_dict = DatasetDict({"train": train_ds, "validation": valid_ds})
    
    return dataset_dict


# Computes metrics for evaluation during training
def compute_metrics(eval_pred):
    logits, labels = eval_pred

    # Get the predictions by finding the class with the highest logit
    predictions = np.argmax(logits, axis=-1)
    accuracy = get_accuracy(labels, predictions)
    
    return {"accuracy": accuracy}


# Trains a model using the HuggingFace Trainer model
def train_model(model, train_dataset, valid_dataset, num_epochs, output_dir, bestmodel_dir):
    training_args = TrainingArguments(
        output_dir=output_dir,          # Directory to save the model
        num_train_epochs=num_epochs,    # Total number of training epochs
        per_device_train_batch_size=8,  # Batch size for training
        per_device_eval_batch_size=8,   # Batch size for evaluation
        logging_steps=50,               # Log every 50 steps
        eval_strategy="epoch",          # Run evaluation at the end of each epoch
        save_strategy="epoch",          # Save the model at the end of each epoch
        load_best_model_at_end=True,    # Load the best model found during training
    )

    # Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        compute_metrics=compute_metrics,
    )

    # Start training
    trainer.train()

    # Save the best performing model
    trainer.save_model(os.path.join(output_dir, bestmodel_dir))

    # After training, get the final evaluation results
    eval_results = trainer.evaluate()
    print(f"\nEvaluation Results:\n{eval_results}")


# Loads the trained model
def load_trained_model(model_dir, model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    return tokenizer, model


# Predicts subject-verb agreement in a given sentence
def predict_sva(tokenizer, loaded_model, sentence):
    # Tokenize the input text
    inputs = tokenizer(sentence, return_tensors="pt", padding=True, truncation=True).to(loaded_model.device)

    # Get model output
    with torch.no_grad():
        logits = loaded_model(**inputs).logits
        
    # Get the predicted class ID
    predicted_class_id = logits.argmax().item()
    
    return 1 if loaded_model.config.id2label[predicted_class_id] == "LABEL_1" else 0


# Returns a subset of size train_size of the training data
def decide_train_size(pd_train, train_size):
    # Identify how many samples to get for each class
    classes = pd_train["label"].unique()
    num_classes = len(classes) # 2 classes in this case
    samples_per_class = train_size // num_classes

    # Iterate over each class and collect samples
    total_samples = []
    for c in classes:
        class_subset = pd_train[pd_train["label"] == c]
        num_class_samples = min(samples_per_class, len(class_subset))    
        class_samples = class_subset.sample(num_class_samples)
        total_samples.append(class_samples)
    pd_sampled_train = pd.concat(total_samples)

    # If the number of collected samples is not equal to the train_size, then randomly collect more samples
    if len(pd_sampled_train) < train_size:
        num_missing = train_size - len(pd_sampled_train)
        pd_sampled_train = pd.concat([pd_sampled_train, pd_train.drop(pd_sampled_train.index).sample(n=num_missing)])

    # Shuffle the samples
    pd_sampled_train = pd_sampled_train.sample(frac=1, random_state=42).reset_index(drop=True)

    return pd_sampled_train


# Calculates accuracy from the given ground truth and predicted labels
def get_accuracy(list_gt, list_pred):
    total_predictions = 0
    correct_predictions = 0

    for i in range(len(list_pred)):
        total_predictions += 1
        if list_pred[i] == list_gt[i]:
            correct_predictions += 1

    accuracy = correct_predictions / total_predictions

    return accuracy


# Tests the given model
def test(model_name, model_dir, pl_data):
    tokenizer, model = load_trained_model(model_dir, model_name)
    pl_data = pl_data.with_columns(prediction = pl.col("sentence").map_elements(lambda x: predict_sva(tokenizer, model, x)))
    return get_accuracy(pl_data["label"].to_list(), pl_data["prediction"].to_list())


# Creates an LLM for SVA classification
def create_llm():
    # Set the train size and epoch
    with open("./data/train_sva_data.json", "r", encoding="utf-8") as fp:
        train_data = json.load(fp)
    train_size = len(train_data)
    epoch = 1
   
    # Load training, valid, and test dataset as polars dataframes
    pl_train = pl.read_json("./data/train_sva_data.json").to_pandas()
    pl_train = decide_train_size(pl_train, train_size) 
    pl_valid = pl.read_json("./data/valid_sva_data.json").to_pandas()

    # Create dataset dictionary
    dataset = convert_df_to_dataset(pl_train, pl_valid)

    # Load model and tokenizer
    tokenizer, model = load_model_and_tokenizer()

    # Tokenize the created dataset
    tokenized_datasets = dataset.map(lambda x: tokenize_function(tokenizer, x), batched=True)
    train_dataset = tokenized_datasets["train"]
    valid_dataset = tokenized_datasets["validation"]

    # Train the model
    train_model(model, train_dataset, valid_dataset, epoch, "./llm", "best_llm")
    
    # Mini sample output
    pos_sentence = "The duck walks up to the lemonade stand ."  # expected: 1
    neg_sentence = "The duck walk up to the lemonade stand ."  # expected: 0
    print(f"Sentence: '{pos_sentence}' -> SVA: {predict_sva(tokenizer, model, pos_sentence)}")
    print(f"Sentence: '{neg_sentence}' -> SVA: {predict_sva(tokenizer, model, neg_sentence)}")


# Tests the created LLM
def test_created_llm():
    pl_test = pl.read_json("./data/test_sva_data.json")
    model_dir = "./llm/best_llm"
    test_accuracy = test("distilbert-base-uncased", model_dir, pl_test)
    return test_accuracy
