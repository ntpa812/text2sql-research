import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

model_path = "/mnt/e/proton-intern/javisAI/6804_ddq/Text2SQL_Template/models/mars-sql/mars-sql_qwen_sql_7b"

torch.cuda.empty_cache()

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=False,   
    bnb_4bit_quant_type="nf4",
)

tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    trust_remote_code=True,
    local_files_only=True
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map={"": 0},   
    trust_remote_code=True,
    local_files_only=True,
)

model.config.use_cache = False  

prompt = """
You are a SQL expert.
Convert the following question into SQL.

Question: List all customers with balance > 1000
SQL:
"""

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=64, 
        temperature=0.1
    )

print(tokenizer.decode(outputs[0], skip_special_tokens=True))