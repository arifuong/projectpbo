"""
Entry Point Utama Web Application - Sistem Validasi RPS & BAP.

Modul ini mem-boot aplikasi Flask menggunakan Application Factory Pattern
dan memicu web server lokal.
"""

import os
from app import create_app
from utils.logger import setup_logger

# Inisialisasi logger utama untuk web bootloader
logger = setup_logger("web_main")

# Bentuk aplikasi Flask dengan konfigurasi default
app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    
    logger.info(f"Memulai Server Flask di http://{host}:{port} (debug={debug})...")
    
    # Jalankan web server Flask
    app.run(host=host, port=port, debug=debug)
