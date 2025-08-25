import time
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap import Window
from ttkbootstrap.constants import *

from extractor import URLExtractor
from file_handler import FileHandler
from llm_classifier import LLMClassifier


class URLExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("URL Content Extractor")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        self.stop_requested = False

        # Değişkenler
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        # Extractor ve FileHandler
        self.extractor = URLExtractor(timeout=10, delay=0.1)
        self.file_handler = FileHandler()
        self.llm_classifier = LLMClassifier()
        self.processing = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Ana UI bileşenlerini oluştur"""
        # Ana frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Grid yapılandırması
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self._create_header(main_frame)
        self._create_file_selection(main_frame)
        self._create_buttons(main_frame)
        self._create_progress_bar(main_frame)
        self._create_status_area(main_frame)
        
        # Grid weights for resizing
        main_frame.rowconfigure(6, weight=1)

        # İlk mesaj
        self.log_message("Ready to start. Please select input and output files.")

    def _create_header(self, parent):
        """Başlık oluştur"""
        title_label = ttk.Label(parent, text="URL Content Extractor",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

    def _create_file_selection(self, parent):
        """Dosya seçim bileşenlerini oluştur"""
        # Input file seçimi
        ttk.Label(parent, text="Input File (.txt):", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5)

        input_entry = ttk.Entry(parent, textvariable=self.input_file_path,
                               width=50, state="readonly")
        input_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)

        input_browse_btn = ttk.Button(parent, text="Browse",
                                     command=self.browse_input_file)
        input_browse_btn.grid(row=1, column=2, padx=(5, 0), pady=5)

        # Output file seçimi
        ttk.Label(parent, text="Output File (.csv):", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky=tk.W, pady=5)

        output_entry = ttk.Entry(parent, textvariable=self.output_file_path,
                                width=50, state="readonly")
        output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)

        output_browse_btn = ttk.Button(parent, text="Browse",
                                      command=self.browse_output_file)
        output_browse_btn.grid(row=2, column=2, padx=(5, 0), pady=5)

        # Ayırıcı çizgi
        separator = ttk.Separator(parent, orient=tk.HORIZONTAL)
        separator.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)

    def _create_buttons(self, parent):
        """Ana butonları oluştur"""
        # Butonlar için yeni frame (ortalanmış, yan yana ve boşluklu)
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        # Butonları oluştur
        self.process_btn = ttk.Button(button_frame, text="Start Extraction", 
                                     style="Accent.TButton", command=self.start_extraction)
        self.stop_btn = ttk.Button(button_frame, text="Stop Extraction", 
                                  style="Danger.TButton", command=self.stop_extraction)

        # Butonları yan yana, ortalanmış ve aralarında 10px boşlukla pack et
        self.process_btn.pack(side="left", padx=(0, 10))
        self.stop_btn.pack(side="left")

        # Başlangıçta Stop butonunu pasif yap
        self.stop_btn.config(state="disabled")

    def _create_progress_bar(self, parent):
        """Progress bar oluştur"""
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

    def _create_status_area(self, parent):
        """Status area oluştur"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="10")
        status_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)

        # Status text area
        self.status_text = tk.Text(status_frame, height=8, width=70,
                                   wrap=tk.WORD, state=tk.DISABLED, bg="#f9f9f9", font=("Consolas", 10))
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar for status text
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL,
                                         command=self.status_text.yview)
        status_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=status_scrollbar.set)

    # Event handlers
    def browse_input_file(self):
        """Input dosyası seçimi için dialog"""
        file_path = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file_path.set(file_path)
            self.log_message(f"Input file selected: {os.path.basename(file_path)}")
            
    def browse_output_file(self):
        """Output dosyası seçimi için dialog"""
        file_path = filedialog.asksaveasfilename(
            title="Save Output File",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.output_file_path.set(file_path)
            self.log_message(f"Output file set: {os.path.basename(file_path)}")

    def log_message(self, message):
        """Status area'ya mesaj ekle"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)  # En son mesaja kaydır
        self.status_text.config(state=tk.DISABLED)
        self.root.update()  # GUI'yi güncelle

    def stop_extraction(self):
        """Kullanıcı işlemi iptal ettiğinde çağrılır"""
        if not self.processing:
            return
        self.stop_requested = True
        self.log_message("❌ Extraction stopped by user.")
        self.progress_var.set(0)
        self.process_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def start_extraction(self):
        """Ana işlemi başlat"""
        if self.processing:
            return  # Eğer zaten işleniyorsa yeni işlem başlatma

        # Dosya kontrolü
        if not self.input_file_path.get():
            messagebox.showerror("Error", "Please select an input file.")
            return

        if not self.output_file_path.get():
            messagebox.showerror("Error", "Please select an output file location.")
            return

        # Dosya doğrulaması
        validation = self.file_handler.validate_txt_file(self.input_file_path.get())
        if not validation['valid']:
            error_msg = "File validation failed:\n" + "\n".join(validation['errors'])
            messagebox.showerror("Validation Error", error_msg)
            return

        self.log_message(f"Found {validation['url_count']} URLs to process")

        # Buton durumları ayarlanır
        self.process_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.stop_requested = False
        self.processing = True
        self.progress_var.set(0)

        # Threading ile işlemi başlat
        thread = threading.Thread(target=self.run_extraction)
        thread.daemon = True
        thread.start()

    def run_extraction(self):
        """Ana extraction işlemi"""
        try:
            # LLM bağlantı kontrolü
            self.log_message("Checking connection with the LLM model...")
            start_llm = time.time()
            llm_ok = self.llm_classifier.is_llm_available()
            llm_duration = time.time() - start_llm

            if llm_ok:
                self.log_message("✅ Connection successful. LLM classification is enabled.")
            else:
                self.log_message("❌ Failed to connect to the LLM model. Classification will be skipped.")

            # URL'leri oku
            self.log_message("Reading URLs from file...")
            urls = self.file_handler.read_urls_from_txt(self.input_file_path.get())
            start_extraction = time.time()

            def progress_callback(progress, message):
                self.root.after(0, lambda: self.update_progress(progress, message))

            def stop_flag():
                return self.stop_requested

            # URL'lerden içerik çıkar
            self.log_message("Starting content extraction...")
            results = self.extractor.extract_multiple_urls(urls, progress_callback, stop_flag=stop_flag)

            extraction_duration = time.time() - start_extraction

            timing_info = {
                'llm_check_duration': llm_duration,
                'extraction_duration': extraction_duration
            }

            def save_csv():
                successful_results = [r for r in results if r['status'] == 'success']
                self.log_message(f"Writing {len(successful_results)} successful results to CSV...")
                self.file_handler.write_results_to_csv(successful_results, self.output_file_path.get())
                total_count = len(results)
                success_count = len(successful_results)
                final_message = f"Saved {success_count} successful results out of {total_count} total URLs."
                self.progress_var.set(0)
                self.stop_btn.config(state="disabled")
                self.log_message(final_message)
                messagebox.showinfo("Success", final_message)

            self.root.after(0, lambda: self.show_preview(results, on_confirm=save_csv, timing_info=timing_info))

        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            self.root.after(0, lambda: self.log_message(f"ERROR: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))

        finally:
            self.root.after(0, self.finish_extraction)

    def update_progress(self, progress, message):
        """Progress bar ve mesajı güncelle"""
        self.progress_var.set(progress)
        self.log_message(message)

    def finish_extraction(self):
        """Extraction tamamlandığında GUI'yi normale döndür"""
        self.processing = False
        self.process_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_var.set(0)

    # Preview window ayrı bir dosyaya taşınacak, şimdilik import ile çağrılacak
    def show_preview(self, results, on_confirm, timing_info=None):
        """Preview window'u göster - ayrı dosyadan import edilecek"""
        from .preview_window import PreviewWindow
        preview = PreviewWindow(self.root, self.extractor)
        preview.show(results, on_confirm, timing_info)