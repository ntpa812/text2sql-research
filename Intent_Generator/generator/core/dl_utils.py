import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel, PeftConfig
import os

class LocalParaphraser:
    def __init__(self, model_path="models/my_banking_ai"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_ready = False
        
        if not os.path.exists(model_path):
            print(f"⚠ Cảnh báo: Không tìm thấy model tại {model_path}. Sẽ trả về text gốc.")
            return

        print(f"[*] Đang tải AI Model từ {model_path} lên {self.device}...")
        try:
            config = PeftConfig.from_pretrained(model_path)
            
            self.tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)
            base_model = AutoModelForSeq2SeqLM.from_pretrained(config.base_model_name_or_path)
            
            self.model = PeftModel.from_pretrained(base_model, model_path).to(self.device)
            self.model.eval() 
            
            self.is_ready = True
            print("> AI Model đã sẵn sàng hoạt động!")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo AI: {e}")

    def paraphrase(self, text, num_return=1):
        if not self.is_ready:
            return [text] 

        input_text = f"paraphrase: {text}"
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                max_length=128,
                num_beams=5,            
                num_return_sequences=num_return,
                temperature=0.7,        
                do_sample=True,        
                early_stopping=True
            )
        
        results = []
        for output in outputs:
            decoded_text = self.tokenizer.decode(output, skip_special_tokens=True)
            results.append(decoded_text)
            
        return list(set(results))