import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

class NER:
    def __init__(self, model_path='/home/javis-ai/project/llms/weights/NER/ver2'):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.entity_types = ['O', 'B-MONEY', 'I-MONEY', 'B-ACCN', 'I-ACCN', 'B-BANK', 'I-BANK']
        self.id2label = {i: label for i, label in enumerate(self.entity_types)}
        self.label2id = {label: i for i, label in enumerate(self.entity_types)}

        if not self.model_path:
            print('Model path not found')

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForTokenClassification.from_pretrained(
                self.model_path,
                id2label = self.id2label,
                label2id=self.label2id
            )
            self.model.eval()
            print('Successfully loading model')
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tải model từ '{self.model_path}': {e}")

    def convert_money_form(self, money: str) -> str:
        money = money.lower().replace('.', '').replace(' ', '')
        
        type1 = ['k', 'nghìn', 'ngàn']
        for s in type1:
            if money.endswith(s):
                money = money.replace(s, '') + '000'
                return money
        
        type2 = ['triệu', 'tr', 'củ']
        for s in type2:
            if money.endswith(s):
                money = money.replace(s, '') + '000000'
                return money
        
        type3 = ['tỉ', 't']
        for s in type3:
            if money.endswith(s):
                money = money.replace(s, '') + '000000000'
                return money
        
        return money

    def run(self, text):
        if self.model is None or self.tokenizer is None:
            print("Lỗi: Model hoặc tokenizer chưa được tải. Vui lòng kiểm tra lại đường dẫn model.")
            return []

        text = text.strip().rstrip('.')
        inputs = self.tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predictions = torch.argmax(logits, dim=2)

        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        pred_labels = [self.id2label[pred_id] for pred_id in predictions[0].tolist()]

        full_entities = []
        current_entity_word = ""
        current_entity_label = None

        # Loop through tokens to reassemble words and their labels
        for token, label in zip(tokens, pred_labels):
            # Skip special tokens
            if token in [self.tokenizer.cls_token, self.tokenizer.sep_token]:
                continue
            
            # Remove "B-" or "I-" prefix for logic
            clean_label = label.split('-')[-1]
            
            # Check if this token is the start of a new entity
            if label.startswith("B-"):
                # If there was a previous entity, save it
                if current_entity_word:
                    # Filter for desired labels before saving
                    if current_entity_label in ["MONEY", "ACCN", "BANK"]:
                        if current_entity_label == "MONEY":
                            current_entity_word = self.convert_money_form(current_entity_word)
                        full_entities.append({
                            "entity": current_entity_word.replace('@', ''),
                            "label": current_entity_label
                        })

                # Start a new entity
                current_entity_word = token.lstrip("##")
                current_entity_label = clean_label
            # Check if this token is part of the current entity
            elif label.startswith("I-") and clean_label == current_entity_label:
                # Append to the current word, removing the "##" prefix
                current_entity_word += token.lstrip("##")
            else:
                # If the tag is "O" or a different entity, save the previous entity and reset
                if current_entity_word:
                    if current_entity_label in ["MONEY", "ACCN", "BANK"]:
                        if current_entity_label == "MONEY":
                            current_entity_word = self.convert_money_form(current_entity_word)
                        full_entities.append({
                            "entity": current_entity_word.replace('@',''),
                            "label": current_entity_label
                        })
                
                # Reset
                current_entity_word = ""
                current_entity_label = None
        
        # Add the last entity if it exists
        if current_entity_word and current_entity_label in ["MONEY", "ACCN", "BANK"]:
            if current_entity_label == "MONEY":
                current_entity_word = self.convert_money_form(current_entity_word)
            full_entities.append({
                "entity": current_entity_word.replace('@',''),
                "label": current_entity_label
            })
            
        return full_entities

if __name__ == "__main__":
    predictor = NER()
    results = predictor.run('Chuyển 500k đến tài khoản 374889027 VIB')
    print("results:",results)
    for res in results:
        print(res['entity'], res['label'])
