class Translate:
    def translate_zh_to_en(self, text):
        translation = {
            "大模型": "Large Model"
        }
        return translation.get(text,f"无翻译，原文:{text}")

    def translate_en_to_zh(self, text):
        translation = {
            "Large Model":"大模型"
        }
        return translation.get(text,f"None translations,original:{text}")

    def summarize(self,text):
        pass

trs = Translate()