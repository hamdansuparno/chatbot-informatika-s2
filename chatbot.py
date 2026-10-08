"""
chatbot.py
==========
Mesin inferensi Chatbot Machine Learning dan antarmuka CLI.
Mengklasifikasikan pesan teks ke dalam Intent berdasarkan model TF-IDF + Logistic Regression.
"""

import os
import sys
import random
import joblib
import numpy as np

# Pastikan output konsol mendukung UTF-8 di Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from nlp_utils import clean_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE_DIR, "chatbot_model.pkl")

FALLBACK_RESPONSES = [
    "Maaf, saya belum memahami pertanyaan tersebut. Bisa tolong ulangi dengan kalimat lain?",
    "Pertanyaan Anda menarik, tetapi belum ada dalam data latih saya. Silakan coba tanyakan hal lain seputar machine learning, data mining, atau ketik 'bantuan'.",
    "Mohon maaf, saya belum mengerti maksudnya. Anda bisa ketik 'bantuan' untuk melihat daftar topik yang saya kuasai."
]

class ChatbotEngine:
    def __init__(self, model_path: str = MODEL_FILE, confidence_threshold: float = 0.35):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.pipeline = None
        self.responses = {}
        self.tags = []
        self.load_model()

    def load_model(self):
        """Memuat model Machine Learning yang telah dilatih."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model '{self.model_path}' belum ditemukan! "
                "Silakan jalankan 'python train_chatbot.py' terlebih dahulu."
            )
        
        data = joblib.load(self.model_path)
        self.pipeline = data["pipeline"]
        self.responses = data["responses"]
        self.tags = data.get("tags", [])

    def predict_intent(self, text: str):
        """
        Mengekstrak fitur TF-IDF dan memprediksi intent menggunakan model klasifikasi.
        Mengembalikan: (predicted_tag, confidence_score, all_probabilities_dict)
        """
        cleaned = clean_text(text)
        if not cleaned:
            return None, 0.0, {}

        # Dapatkan probabilitas untuk setiap kelas intent
        probs = self.pipeline.predict_proba([cleaned])[0]
        classes = self.pipeline.classes_
        
        max_idx = int(np.argmax(probs))
        predicted_tag = classes[max_idx]
        confidence = float(probs[max_idx])

        # Urutkan probabilitas dari yang tertinggi
        prob_dict = {classes[i]: float(probs[i]) for i in range(len(classes))}
        sorted_probs = dict(sorted(prob_dict.items(), key=lambda item: item[1], reverse=True))

        return predicted_tag, confidence, sorted_probs

    def get_response(self, user_input: str):
        """
        Menghasilkan respons chatbot berdasarkan teks pengguna.
        Mengembalikan dict berisi: response, intent, confidence, status
        """
        if not user_input or not user_input.strip():
            return {
                "response": "Silakan ketikkan pesan atau pertanyaan Anda.",
                "intent": "empty",
                "confidence": 0.0,
                "is_fallback": True
            }

        predicted_tag, confidence, all_probs = self.predict_intent(user_input)

        if predicted_tag is None or confidence < self.confidence_threshold:
            return {
                "response": random.choice(FALLBACK_RESPONSES),
                "intent": predicted_tag if predicted_tag else "unknown",
                "confidence": confidence,
                "is_fallback": True,
                "probabilities": all_probs
            }

        # Ambil respons acak dari kumpulan respons intent yang cocok
        possible_responses = self.responses.get(predicted_tag, FALLBACK_RESPONSES)
        chosen_response = random.choice(possible_responses)

        return {
            "response": chosen_response,
            "intent": predicted_tag,
            "confidence": confidence,
            "is_fallback": False,
            "probabilities": all_probs
        }

def run_cli():
    print("=" * 65)
    print("   [+] CHATBOT MACHINE LEARNING (NLP INTENT CLASSIFICATION)")
    print("=" * 65)
    print(" - Ketik pertanyaan Anda dalam Bahasa Indonesia.")
    print(" - Ketik 'keluar' atau 'exit' untuk mengakhiri percakapan.")
    print(" - Ketik 'bantuan' untuk melihat daftar topik yang tersedia.")
    print("=" * 65)

    try:
        bot = ChatbotEngine()
        print("[OK] Model berhasil dimuat. Siap melayani!\n")
    except Exception as e:
        print(f"[!] Terjadi kesalahan saat memuat model: {e}")
        return

    while True:
        try:
            user_input = input("\n[Anda]: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["keluar", "exit", "quit", "bye", "dadah"]:
                print("\n[Bot]: Sampai jumpa lagi! Terima kasih sudah mencoba chatbot ini.")
                break

            result = bot.get_response(user_input)
            
            # Tampilkan respons bot beserta rincian machine learning
            conf_percent = result["confidence"] * 100
            print(f"[Bot] : {result['response']}")
            print(f"        (Intent: '{result['intent']}' | Confidence: {conf_percent:.1f}%)")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSesi diakhiri. Sampai jumpa!")
            break

if __name__ == "__main__":
    run_cli()
