# -*- coding: utf-8 -*-
"""
Vietnamese Text Corrector Class

A reusable class for fixing Vietnamese text errors (OCR errors, missing diacritics, etc.)
using the ProtonX Legal Text Correction models.

Supported models:
- Teacher: protonx-models/protonx-legal-tc (best quality, max 160 tokens)
- Student: protonx-models/distilled-protonx-legal-tc (balanced, max 128 tokens)
- Nano: protonx-models/nano-protonx-legal-tc (fastest, max 160 tokens)
"""

import os
from pathlib import Path
from typing import List, Optional, Literal
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


ModelType = Literal["teacher", "student", "nano"]


class VietnameseTextCorrector:
    """
    A class to correct Vietnamese text errors using pre-trained Seq2Seq models.
    
    Attributes:
        model_type (str): Type of model to use ('teacher', 'student', or 'nano')
        max_tokens (int): Maximum tokens for generation
        num_beams (int): Number of beams for beam search
        chunk_size (int): Number of words per chunk for long text processing
    
    Example:
        >>> corrector = VietnameseTextCorrector(model_type="teacher")
        >>> result = corrector.correct("Căn cứ Luat An toan thông tin mạng")
        >>> print(result)
        Căn cứ Luật An toàn thông tin mạng
    """
    # Default local path for downloaded models
    # Get the directory where this script is located and go up to find data_models
    _SCRIPT_DIR = Path(__file__).parent.parent
    LOCAL_MODEL_DIR = _SCRIPT_DIR / "data_models" / "fix_Vietnamese_errors_models"
    
    # HuggingFace model identifiers
    HF_MODEL_PATHS = {
        "teacher": "protonx-models/protonx-legal-tc",
        "student": "protonx-models/distilled-protonx-legal-tc",
        "nano": "protonx-models/nano-protonx-legal-tc"
    }
    
    # Local directory names for each model type
    LOCAL_MODEL_NAMES = {
        "teacher": "protonx-legal-tc",
        "student": "distilled-protonx-legal-tc",
        "nano": "nano-protonx-legal-tc"
    }
    
    DEFAULT_MAX_TOKENS = {
        "teacher": 160,
        "student": 128,
        "nano": 160
    }
    
    def __init__(
        self,
        model_type: ModelType = "teacher",
        max_tokens: Optional[int] = None,
        num_beams: int = 10,
        chunk_size: int = 24,
        device: Optional[str] = None
    ):
        """
        Initialize the Vietnamese Text Corrector.
        
        Models are automatically downloaded to `data_models/fix_Vietnamese_errors_models`
        if not already present locally.
        
        Args:
            model_type: Type of model to use ('teacher', 'student', or 'nano')
            max_tokens: Maximum tokens for generation (uses model default if None)
            num_beams: Number of beams for beam search (default: 10)
            chunk_size: Number of words per chunk for long text (default: 24)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        if model_type not in self.HF_MODEL_PATHS:
            raise ValueError(f"Invalid model_type: {model_type}. Must be one of {list(self.HF_MODEL_PATHS.keys())}")
        
        self.model_type = model_type
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS[model_type]
        self.num_beams = num_beams
        self.chunk_size = chunk_size
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Get or download the model
        model_path = self._get_or_download_model(model_type)
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"[VietnameseTextCorrector] Loaded model: {model_path} on {self.device}")
    
    def _get_or_download_model(self, model_type: ModelType) -> str:
        """
        Get local model path, downloading from HuggingFace if not present.
        
        Args:
            model_type: Type of model ('teacher', 'student', or 'nano')
            
        Returns:
            Path to the local model directory
        """
        # Ensure local model directory exists
        self.LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        local_model_path = self.LOCAL_MODEL_DIR / self.LOCAL_MODEL_NAMES[model_type]
        hf_model_id = self.HF_MODEL_PATHS[model_type]
        
        # Check if model already exists locally
        if self._is_model_valid(local_model_path):
            print(f"[VietnameseTextCorrector] Found local model at: {local_model_path}")
            return str(local_model_path)
        
        # Download model from HuggingFace
        print(f"[VietnameseTextCorrector] Model not found locally. Downloading from HuggingFace: {hf_model_id}")
        print(f"[VietnameseTextCorrector] Saving to: {local_model_path}")
        
        # Download and save tokenizer
        tokenizer = AutoTokenizer.from_pretrained(hf_model_id)
        tokenizer.save_pretrained(str(local_model_path))
        
        # Download and save model
        model = AutoModelForSeq2SeqLM.from_pretrained(hf_model_id)
        model.save_pretrained(str(local_model_path))
        
        print(f"[VietnameseTextCorrector] Successfully downloaded and saved model to: {local_model_path}")
        
        return str(local_model_path)
    
    def _is_model_valid(self, model_path: Path) -> bool:
        """
        Check if a local model directory contains valid model files.
        
        Args:
            model_path: Path to the local model directory
            
        Returns:
            True if the model directory exists and contains required files
        """
        if not model_path.exists():
            return False
        
        # Check for essential files (config.json is always required)
        required_files = ["config.json"]
        # Model can be in .bin or .safetensors format
        model_files = ["pytorch_model.bin", "model.safetensors"]
        
        for req_file in required_files:
            if not (model_path / req_file).exists():
                return False
        
        # Check if at least one model file exists
        has_model_file = any((model_path / mf).exists() for mf in model_files)
        if not has_model_file:
            return False
        
        return True
    
    def correct(self, text: str) -> str:
        """
        Correct a single text input.
        
        Args:
            text: The Vietnamese text to correct
            
        Returns:
            The corrected text
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_tokens
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                num_beams=self.num_beams,
                num_return_sequences=1,
                max_new_tokens=self.max_tokens,
                early_stopping=True,
            )
        
        decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return decoded
    
    def correct_batch(self, texts: List[str]) -> List[str]:
        """
        Correct a batch of text inputs.
        
        Args:
            texts: List of Vietnamese texts to correct
            
        Returns:
            List of corrected texts
        """
        results = []
        for text in texts:
            result = self.correct(text)
            results.append(result)
        return results
    
    def _split_into_word_chunks(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """
        Split text into chunks of specified word count.
        
        Args:
            text: The text to split
            chunk_size: Number of words per chunk (uses instance default if None)
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        words = text.split()
        return [
            " ".join(words[i:i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
    
    def correct_long_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        verbose: bool = False
    ) -> str:
        """
        Correct long text by splitting into chunks and processing each chunk.
        
        This method is useful for texts longer than the model's context window.
        
        Args:
            text: The long Vietnamese text to correct
            chunk_size: Number of words per chunk (uses instance default if None)
            verbose: Whether to print progress information
            
        Returns:
            The corrected text (concatenated from all chunks)
        """
        chunk_size = chunk_size or self.chunk_size
        chunks = self._split_into_word_chunks(text, chunk_size)
        
        if verbose:
            print(f"\nTotal chunks: {len(chunks)}")
            print("=" * 50)
        
        decoded_all = []
        
        for idx, chunk in enumerate(chunks, 1):
            if verbose:
                print(f"\n### Decoding chunk {idx}/{len(chunks)}")
                print(f"Chunk: {chunk}")
            
            best_decoded = self.correct(chunk)
            
            if verbose:
                print(f"→ Decoded: {best_decoded}")
            
            decoded_all.append(best_decoded)
        
        final_output = " ".join(decoded_all).strip()
        return final_output
    
    def correct_with_scores(self, text: str, num_return_sequences: int = 1) -> List[dict]:
        """
        Correct text and return results with beam scores.
        
        Args:
            text: The Vietnamese text to correct
            num_return_sequences: Number of sequences to return (default: 1)
            
        Returns:
            List of dicts containing 'text' and 'score' for each result
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_tokens
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                num_beams=self.num_beams,
                num_return_sequences=num_return_sequences,
                max_new_tokens=self.max_tokens,
                early_stopping=True,
                return_dict_in_generate=True,
                output_scores=True
            )
        
        sequences = outputs.sequences
        scores = outputs.sequences_scores
        
        results = []
        for seq, score in zip(sequences, scores):
            decoded = self.tokenizer.decode(seq, skip_special_tokens=True)
            results.append({
                "text": decoded,
                "score": float(score)
            })
        
        return results


# -----------------------------
# Standalone test when running this file directly
# -----------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Vietnamese Text Corrector - Test Mode")
    print("=" * 60)
    
    # Test examples
    test_examples = [
        "THÉ SINH VIEN",
        "DAI Hoc ACB",
        "QUY ĐỊNH CHI TI3T VÀ HƯỚNG DaN MỘT SỐ ĐIeU CỦA NGHỊ ĐiNH SỐ 85/2016/NĐ-CP",
        "Căn cứ Luat An toan thông tin mạng ngay 19 tháng 11 nom 2015",
        "Nhà nuoc cong hoa xa hoi chu nghia Viet nam",
        "an ninh mang",
        "NHUNGQUYDINHCHUNG",
        "truyen thong trong nuoc cho rang",
        "can cu bo luat lao dong 2019 va cac van ban huong dan thuc hien.",
    ]
    
    # Initialize corrector (using teacher model by default)
    print("\n>>> Initializing VietnameseTextCorrector (teacher model)...")
    corrector = VietnameseTextCorrector(model_type="teacher")
    
    print("\n" + "=" * 60)
    print("Testing correct() method:")
    print("=" * 60)
    from time import time
    for text in test_examples:
        t0=time()
        result = corrector.correct(text)
        print(f"\nInput:  {text}")
        print(f"Output: {result}")
        print(time()-t0)
        print("-" * 40)
    
    # Test long text processing
    print("\n" + "=" * 60)
    print("Testing correct_long_text() method:")
    print("=" * 60)
    
    long_text = "hom nay toi den vanphong de nop ho so nhung gap tinhtrang may in bi loi nen toi phai doi rat lau, nhanvien bao rang he thong dang capnhat nen moi nguoi thongcam, nhung toi van thay rat bat tien va mat nhieu thoi gian cho viec nay."
    
    result = corrector.correct_long_text(long_text, chunk_size=12, verbose=True)
    print("\n" + "=" * 60)
    print("FINAL OUTPUT:")
    print(result)
    print("=" * 60)
    
    # Test batch processing
    print("\n" + "=" * 60)
    print("Testing correct_batch() method:")
    print("=" * 60)
    
    batch_texts = [
        "Dièu 1.Pham vi dièu chinh",
        "Am Thuc Thai Linh",
        "Nguyên Bá Ngọc",
    ]
    
    batch_results = corrector.correct_batch(batch_texts)
    
    for input_text, output_text in zip(batch_texts, batch_results):
        print(f"\nInput:  {input_text}")
        print(f"Output: {output_text}")
        print("-" * 40)
    
    # Test with scores
    print("\n" + "=" * 60)
    print("Testing correct_with_scores() method:")
    print("=" * 60)
    
    text_for_scores = "của Chính phủ về bao đam an toàn hệ thống thông tin theo cấp độ"
    results_with_scores = corrector.correct_with_scores(text_for_scores, num_return_sequences=3)
    
    print(f"\nInput: {text_for_scores}\n")
    for i, result in enumerate(results_with_scores, 1):
        print(f"Beam {i} | Score: {result['score']:.4f}")
        print(f"Text: {result['text']}")
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
