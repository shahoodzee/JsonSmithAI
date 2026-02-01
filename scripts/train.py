import argparse
import json
import os
from pathlib import Path
from typing import Any, List, Dict, Tuple

import torch
from torch.utils.data import Dataset
from PIL import Image
from transformers import (
    VisionEncoderDecoderConfig,
    VisionEncoderDecoderModel,
    DonutProcessor,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

class JsonImageDataset(Dataset):
    """
    Dataset for Donut model.
    Expected structure:
    dataset_path/
        metadata.jsonl  (lines: {"file_name": "image.jpg", "text": "{\"json\": \"...\"}"})
        image.jpg
        ...
    """
    def __init__(
        self,
        dataset_path: str,
        processor: DonutProcessor,
        split: str = "train",
        max_length: int = 768,
        ignore_id: int = -100,
        task_start_token: str = "<s>",
        prompt_end_token: str = None,
        sort_json_key: bool = True,
    ):
        super().__init__()
        self.dataset_path = Path(dataset_path)
        self.processor = processor
        self.max_length = max_length
        self.ignore_id = ignore_id
        self.split = split
        self.prompt_end_token = prompt_end_token if prompt_end_token else ""
        self.sort_json_key = sort_json_key
        
        self.gt_token_sequences = []
        self.links = []
        
        # Load metadata
        metadata_path = self.dataset_path / "metadata.jsonl"
        if not metadata_path.exists():
            raise FileNotFoundError(f"metadata.jsonl not found in {dataset_path}")

        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                # Filter split if your metadata supports it, otherwise load all for now or split manually
                # For simplicity in this script, we assume the folder contains the relevant split
                
                image_path = self.dataset_path / entry["file_name"]
                if not image_path.exists():
                    continue

                self.links.append(str(image_path))
                
                # The label is the 'text' field which should be the target JSON string
                json_obj = json.loads(entry["text"])
                json_str = json.dumps(json_obj, sort_keys=self.sort_json_key) + self.processor.tokenizer.eos_token
                self.gt_token_sequences.append(
                    json_str
                )

    def __len__(self):
        return len(self.links)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        image_path = self.links[idx]
        json_str = self.gt_token_sequences[idx]
        
        # Prepare Image
        image = Image.open(image_path).convert("RGB")
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        
        # Prepare Target
        input_ids = self.processor.tokenizer(
            json_str,
            add_special_tokens=False,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).input_ids

        labels = input_ids.clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = self.ignore_id  # model doesn't need to predict pad token
        
        return {
            "pixel_values": pixel_values.squeeze(),
            "labels": labels.squeeze(),
        }

def train(args):
    # 1. Config & Model
    model_name = args.base_model
    config = VisionEncoderDecoderConfig.from_pretrained(model_name)
    
    # Donut specific config adjustments
    config.encoder.image_size = [1280, 960] # standard donut high res
    config.decoder.max_length = args.max_length
    
    processor = DonutProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name, config=config)
    
    # Add task tokens if needed
    # base donut model usually has them, but we can verify or add custom ones here
    
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.decoder_start_token_id = processor.tokenizer.bos_token_id
    
    # 2. Dataset
    train_dataset = JsonImageDataset(
        dataset_path=args.dataset_path,
        processor=processor,
        max_length=args.max_length
    )
    
    print(f"Loaded {len(train_dataset)} training examples.")
    
    # 3. Trainer
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        predict_with_generate=True,
        fp16=torch.cuda.is_available(), # Use mixed precision if GPU available
        logging_steps=10,
        save_steps=100,
        save_total_limit=2,
        remove_unused_columns=False,
    )
    
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=processor.feature_extractor, # Donut trainer expects feature_extractor as tokenizer sometimes for collator
        data_collator=default_data_collator,
    )
    
    # 4. Train
    print("Starting training...")
    trainer.train()
    
    # 5. Save
    print(f"Saving model to {args.output_dir}")
    processor.save_pretrained(args.output_dir)
    model.save_pretrained(args.output_dir)

def default_data_collator(features):
    # Custom collator might be needed to handle pixel_values and labels stacking
    pixel_values = torch.stack([f["pixel_values"] for f in features])
    labels = torch.stack([f["labels"] for f in features])
    return {
        "pixel_values": pixel_values,
        "labels": labels
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="naver-clova-ix/donut-base", help="HuggingFace model name")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to dataset folder containing metadata.jsonl and images")
    parser.add_argument("--output_dir", type=str, default="model_output", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--max_length", type=int, default=768)
    
    args = parser.parse_args()
    
    if not torch.cuda.is_available():
        print("WARNING: CUDA not available. Training will be extremely slow on CPU.")
    
    train(args)
