import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel, PeftConfig

MODEL_PATH = "models/my_banking_ai" 

print("[*] Đang khởi động hệ thống AI...")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Đang chạy trên: {device.upper()}")

try:
    config = PeftConfig.from_pretrained(MODEL_PATH)
    
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)
    base_model = AutoModelForSeq2SeqLM.from_pretrained(config.base_model_name_or_path)
    
    model = PeftModel.from_pretrained(base_model, MODEL_PATH).to(device)
    model.eval() 
    print("Model đã sẵn sàng! (Gõ 'exit' để thoát)")
    
except Exception as e:
    print(f"❌ Lỗi: {e}")
    exit()

def ask_ai(text):
    input_text = f"paraphrase: {text}"
    
    inputs = tokenizer(input_text, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            max_length=128,
            num_beams=5,      
            early_stopping=True,
            temperature=0.3,  
        )
        
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

while True:
    print("-" * 50)
    user_input = input("Bạn: ")
    if user_input.lower() in ["exit", "quit", "thoat"]:
        break
    
    if not user_input.strip(): continue
    
    response = ask_ai(user_input)
    print(f"AI : {response}")