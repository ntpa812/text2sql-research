import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import random

class LocalParaphraser:
    def __init__(self, model_type="specific"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_type = model_type
        self.is_ready = False
        
        self.model_name = "chieunq/vietnamese-sentence-paraphase"
        
        print(f"[*] Đang load Local Model: {self.model_name} ...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
            self.is_ready = True
            print("Model loaded thành công!")
        except Exception as e:
            print(f"❌ Lỗi load model: {e}")

    def paraphrase(self, text: str, num_return_sequences=3) -> list[str]:
        if not self.is_ready:
            return [text]

        input_ids = self.tokenizer(
            text, 
            return_tensors="pt", 
            padding="longest", 
            max_length=128, 
            truncation=True
        ).input_ids.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                max_length=128,
                do_sample=True,      
                top_k=50,
                top_p=0.95,
                num_return_sequences=num_return_sequences,
                temperature=0.6     
            )

        results = []
        for output in outputs:
            line = self.tokenizer.decode(output, skip_special_tokens=True)
            if line.strip() and line.lower() != text.lower():
                results.append(line.strip())
        
        if not results:
            return [text]
            
        return list(set(results))


class BackTranslationParaphraser:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("[*] Đang load cặp model dịch ngược...")
        try:
            from transformers import MarianMTModel, MarianTokenizer
            # Vi -> En
            self.tok_vi_en = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-vi-en")
            self.mod_vi_en = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-vi-en").to(self.device)
            # En -> Vi
            self.tok_en_vi = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-vi")
            self.mod_en_vi = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-vi").to(self.device)
            self.is_ready = True
            print("Back-Translation Ready!")
        except Exception as e:
            print(f"❌ Lỗi load model dịch: {e}")
            self.is_ready = False

    def paraphrase(self, text: str, num_return_sequences=1) -> list[str]:
        if not self.is_ready: return [text]
        
        inputs = self.tok_vi_en(text, return_tensors="pt", padding=True).to(self.device)
        translated = self.mod_vi_en.generate(**inputs, max_length=128)
        en_text = self.tok_vi_en.decode(translated[0], skip_special_tokens=True)
        
        inputs_back = self.tok_en_vi(en_text, return_tensors="pt", padding=True).to(self.device)
        outs = self.mod_en_vi.generate(
            **inputs_back, 
            max_length=128, 
            do_sample=True, 
            top_k=50, 
            num_return_sequences=num_return_sequences
        )
        
        results = []
        for o in outs:
            vi_text = self.tok_en_vi.decode(o, skip_special_tokens=True)
            if vi_text.lower() != text.lower():
                results.append(vi_text)
        return list(set(results)) if results else [text]

if __name__ == "__main__":
    ai = LocalParaphraser()
    print("Input: Tìm danh sách khách hàng có địa chỉ tại Hà Nội")
    print("Output:", ai.paraphrase("Tìm danh sách khách hàng có địa chỉ tại Hà Nội"))