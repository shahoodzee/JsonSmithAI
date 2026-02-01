import re
import json
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
from functools import lru_cache

class JsonExtractorModel:
    def __init__(self, model_path: str = "naver-clova-ix/donut-base"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading model from {model_path} to {self.device}...")
        
        try:
            self.processor = DonutProcessor.from_pretrained(model_path)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load model from {model_path}: {e}")
            self.model = None
            self.processor = None

    def predict(self, image: Image.Image) -> dict:
        if not self.model:
            return {"error": "Model not loaded correctly."}
        
        # Prepare image
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)

        # Generate output
        task_prompt = "<s>" # Start token
        decoder_input_ids = self.processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
        decoder_input_ids = decoder_input_ids.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.model.decoder.config.max_length,
                early_stopping=True,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )
        
        # Decode
        sequence = self.processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(self.processor.tokenizer.eos_token, "").replace(self.processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token
        
        # Post-processing to extract JSON
        return self.token2json(sequence)

    def token2json(self, tokens, is_inner_value=False, added_vocab=None):
        """
        Simple post-processing to convert the output sequence to JSON.
        The model is trained to output a JSON-like string.
        """
        try:
            return json.loads(tokens)
        except Exception:
            # Fallback or custom parsing if the model output is slightly malformed
            # For now return raw string if json parse fails, wrapped in dict
            return {"raw_output": tokens, "error": "Failed to parse JSON"}

# Singleton instance
@lru_cache()
def get_model_service():
    # In production, point this to "model_output"
    # For now, we use base or a safe default if local trained model doesn't exist
    model_path = "model_output" 
    import os
    if not os.path.exists(model_path):
        print(f"Warning: {model_path} not found. Using 'naver-clova-ix/donut-base-finetuned-cord-v2' for demo purposes.")
        model_path = "naver-clova-ix/donut-base-finetuned-cord-v2" # A fine-tuned example effectively
        
    return JsonExtractorModel(model_path)
