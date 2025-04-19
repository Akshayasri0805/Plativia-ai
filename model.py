import google.generativeai as genai

genai.configure(api_key="AIzaSyAjbQSAUfMR_n1A17iyX2IvR6aj2xFMUIA")

models = genai.list_models()
for m in models:
    print(m.name)
