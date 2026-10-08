"""
app_web.py
==========
Server Web interaktif berbasis pustaka bawaan Python (http.server).
Menyediakan antarmuka Web Chat, upload file Excel/CSV,
serta endpoint analisis perbandingan Naive Bayes vs Prediksi Saham.
"""

import os
import sys
import json
import base64
import pandas as pd
from http.server import HTTPServer, BaseHTTPRequestHandler
from chatbot import ChatbotEngine
from train_chatbot import train_model
from compare_stock_models import run_model_comparison

# Pastikan konsol Windows UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
HTML_FILE = os.path.join(WEB_DIR, "index.html")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXCEL_RESULT_FILE = os.path.join(BASE_DIR, "..", "Perbandingan_Naive_Bayes_Saham.xlsx")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Inisialisasi engine chatbot
try:
    bot = ChatbotEngine()
except Exception:
    print("[*] Model belum ditemukan, melatih model terlebih dahulu...")
    train_model()
    bot = ChatbotEngine()

class ChatRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            if os.path.exists(HTML_FILE):
                self._set_headers(200, content_type="text/html")
                with open(HTML_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404, content_type="text/plain")
                self.wfile.write(b"Halaman index.html tidak ditemukan.")

        elif self.path == "/api/status":
            self._set_headers(200)
            status_data = {
                "status": "online",
                "total_tags": len(bot.tags),
                "tags": bot.tags,
                "confidence_threshold": bot.confidence_threshold
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))

        elif self.path == "/api/download_excel":
            if os.path.exists(EXCEL_RESULT_FILE):
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", 'attachment; filename="Perbandingan_Naive_Bayes_Saham.xlsx"')
                self.end_headers()
                with open(EXCEL_RESULT_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404, content_type="text/plain")
                self.wfile.write(b"File Excel perbandingan belum dibuat.")

        elif self.path == "/api/stock_comparison":
            # Ambil data perbandingan dari Excel yang sudah digenerate
            try:
                if not os.path.exists(EXCEL_RESULT_FILE):
                    run_model_comparison()

                excel_path = os.path.abspath(EXCEL_RESULT_FILE)
                df_metrics = pd.read_excel(excel_path, sheet_name="Ringkasan_Performa")
                df_pred = pd.read_excel(excel_path, sheet_name="Data_Prediksi_Uji").head(10)
                df_cm = pd.read_excel(excel_path, sheet_name="Confusion_Matrix")

                data = {
                    "status": "success",
                    "metrics": df_metrics.to_dict(orient="records"),
                    "confusion_matrix": df_cm.to_dict(orient="records"),
                    "sample_predictions": df_pred.to_dict(orient="records"),
                    "excel_download_url": "/api/download_excel"
                }
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        else:
            self._set_headers(404, content_type="text/plain")
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            try:
                payload = json.loads(body.decode("utf-8"))
                user_msg = payload.get("message", "")
                result = bot.get_response(user_msg)
                
                self._set_headers(200)
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/api/upload":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body.decode("utf-8"))
                filename = payload.get("filename", "uploaded_file.csv")
                b64_content = payload.get("content_base64", "")

                file_bytes = base64.b64decode(b64_content)
                save_path = os.path.join(UPLOAD_DIR, filename)

                with open(save_path, "wb") as f:
                    f.write(file_bytes)

                # Baca file menggunakan pandas
                if filename.endswith(".xlsx") or filename.endswith(".xls"):
                    df = pd.read_excel(save_path)
                else:
                    df = pd.read_csv(save_path)

                total_rows, total_cols = df.shape
                columns_list = df.columns.tolist()
                preview = df.head(5).fillna("").to_dict(orient="records")

                # Coba jalankan perbandingan model jika ada kolom numerik / saham
                comparison_result = None
                try:
                    df_metrics, _ = run_model_comparison(file_path=save_path)
                    comparison_result = df_metrics.to_dict(orient="records")
                except Exception as comp_err:
                    comparison_result = {"info": f"Data berhasil diunggah dan dibaca ({total_rows} baris). Analisis spesifik saham: {comp_err}"}

                response_data = {
                    "status": "success",
                    "filename": filename,
                    "total_rows": total_rows,
                    "total_cols": total_cols,
                    "columns": columns_list,
                    "preview": preview,
                    "comparison": comparison_result
                }

                self._set_headers(200)
                self.wfile.write(json.dumps(response_data).encode("utf-8"))

            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif self.path == "/api/retrain":
            try:
                train_model()
                bot.load_model()
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "success", "message": "Model berhasil dilatih ulang!"}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint tidak ditemukan"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Format log konsol ringkas
        sys.stdout.write(f"[HTTP] {self.address_string()} - {args[0]} {args[1]}\n")

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ChatRequestHandler)
    print("=" * 65)
    print("   [+] SERVER WEB CHATBOT MACHINE LEARNING AKTIF")
    print("=" * 65)
    print(f" -> Akses antarmuka Web Chat di : http://localhost:{PORT}")
    print(f" -> Mendukung Percakapan NLP, Perbandingan Naive Bayes, & Upload Excel")
    print(" -> Tekan Ctrl+C di terminal untuk menghentikan server.")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server dihentikan oleh pengguna.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
