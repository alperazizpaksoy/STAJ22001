import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk


class PreviewWindow:
    def __init__(self, parent, extractor):
        self.parent = parent
        self.extractor = extractor

    def show(self, results, on_confirm, timing_info=None):
        """Çıkarılan verilerin önizlemesini gösterir ve kullanıcıya 'Kaydet' / 'İptal' seçeneği sunar"""
        try:
            preview_window = tk.Toplevel(self.parent)
            preview_window.title("Extraction Preview")
            preview_window.geometry("900x600")
            preview_window.minsize(700, 400)
            preview_window.transient(self.parent)  # Ana pencereye bağla
            preview_window.grab_set()  # Modal yap
            
            # Grid configuration
            preview_window.rowconfigure(0, weight=1)
            preview_window.columnconfigure(0, weight=1)

            # Text widget ve scrollbar
            preview_text = tk.Text(preview_window, wrap=tk.WORD, font=("Segoe UI", 10))
            preview_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

            scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=preview_text.yview)
            scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
            preview_text.config(yscrollcommand=scrollbar.set)

            # Preview içeriğini oluştur
            preview_content = self._generate_preview_content(results, timing_info)

            # Text widget'a içeriği ekle
            preview_text.insert(tk.END, "\n".join(preview_content))
            preview_text.config(state=tk.DISABLED)

            # Button frame
            button_frame = ttk.Frame(preview_window, padding=(10, 5))
            button_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

            self._create_buttons(button_frame, preview_window, on_confirm)
            
            # Pencereyi merkeze getir
            self._center_window(preview_window)
            
        except Exception as e:
            self._handle_preview_error(e, on_confirm)

    def _generate_preview_content(self, results, timing_info):
        """Preview içeriğini oluştur"""
        # Results listelerini güvenli şekilde oluştur
        successful_results = []
        failed_results = []
        duplicate_results = []
        
        for result in results:
            if not isinstance(result, dict):
                continue
                
            status = result.get('status', 'unknown')
            if status == 'success':
                successful_results.append(result)
                if result.get('is_duplicate', False):
                    duplicate_results.append(result)
            elif status == 'failed':
                failed_results.append(result)

        preview_content = []
        
        # Header
        preview_content.extend(self._generate_header())
        
        # Timing info
        if timing_info:
            preview_content.extend(self._generate_timing_info(timing_info, len(results)))
        
        # Statistics
        preview_content.extend(self._generate_statistics(results, successful_results, failed_results, duplicate_results))
        
        # Similarity stats
        preview_content.extend(self._generate_similarity_stats())
        
        # Successful results preview
        if successful_results:
            preview_content.extend(self._generate_successful_results_preview(successful_results))
        
        # Failed results
        if failed_results:
            preview_content.extend(self._generate_failed_results_preview(failed_results))
        
        # Duplicate analysis
        if duplicate_results:
            preview_content.extend(self._generate_duplicate_analysis(duplicate_results))
        
        return preview_content

    def _generate_header(self):
        """Header bölümünü oluştur"""
        return [
            "EXTRACTION SUMMARY",
            "=" * 50,
            ""
        ]

    def _generate_timing_info(self, timing_info, total_count):
        """Timing bilgilerini oluştur"""
        content = []
        llm_time = timing_info.get('llm_check_duration', 0)
        extraction_time = timing_info.get('extraction_duration', 0)
        
        content.append(f"⏱️ LLM connection time: {llm_time:.2f} seconds")
        content.append(f"⏱️ Total extraction time: {extraction_time:.2f} seconds")
        if total_count > 0:
            avg_time = extraction_time / total_count
            content.append(f"⏱️ Average per URL: {avg_time:.2f} seconds")
        content.append("")
        
        return content

    def _generate_statistics(self, results, successful_results, failed_results, duplicate_results):
        """İstatistikleri oluştur"""
        return [
            f"Total URLs processed: {len(results)}",
            f"✅ Successful extractions: {len(successful_results)}",
            f"❌ Failed extractions: {len(failed_results)}",
            f"🔄 Duplicate content found: {len(duplicate_results)}",
            ""
        ]

    def _generate_similarity_stats(self):
        """Similarity istatistiklerini oluştur"""
        content = []
        try:
            if hasattr(self.extractor, 'get_similarity_stats'):
                similarity_stats = self.extractor.get_similarity_stats()
                if similarity_stats and isinstance(similarity_stats, dict):
                    content.append("COMPREHENSIVE SIMILARITY ANALYSIS")
                    content.append("-" * 40)
                    content.append(f"Unique content: {similarity_stats.get('unique_count', 0)}")
                    content.append(f"Total duplicates: {similarity_stats.get('total_duplicates', 0)}")
                    content.append(f"Duplicate rate: {similarity_stats.get('duplicate_rate', 0)*100:.1f}%")
                    
                    detection_methods = similarity_stats.get('detection_methods', {})
                    if detection_methods:
                        content.append("")
                        content.append("Duplicate Detection Methods:")
                        for method, count in detection_methods.items():
                            icon = "🧠" if method == "Embedding" else "🔍" if method == "MinHash" else "🔗"
                            content.append(f"  {icon} {method}: {count}")
                    
                    category_stats = similarity_stats.get('category_stats', {})
                    if category_stats:
                        content.append("")
                        content.append("CONTENT BY CATEGORY")
                        content.append("-" * 30)
                        for category, count in sorted(category_stats.items()):
                            content.append(f"📁 {category}: {count} unique URLs")
                        content.append("")
        except Exception as e:
            content.append(f"Note: Could not load similarity statistics: {str(e)}")
            content.append("")
        
        return content

    def _generate_successful_results_preview(self, successful_results):
        """Başarılı sonuçların önizlemesini oluştur"""
        content = [
            "SUCCESSFUL EXTRACTIONS PREVIEW",
            "-" * 50
        ]
        
        display_count = min(10, len(successful_results))
        for i, result in enumerate(successful_results[:display_count]):
            try:
                url = result.get('url', 'Unknown URL')
                title = result.get('title', 'No title')
                child_cat = result.get('child_category', 'Unknown')
                
                content.append(f"{i+1}. URL: {url}")
                content.append(f"   Title: {title}")
                content.append(f"   Category: {child_cat}")
                
                if result.get('is_duplicate'):
                    content.extend(self._format_duplicate_info(result))
                
                summary = result.get('summary', '')
                if summary:
                    content.append(f"   Summary: {summary}")
                
                content_text = result.get('content', '')
                if content_text:
                    content_preview = content_text[:200] + "..." if len(content_text) > 200 else content_text
                    content.append(f"   Content preview: {content_preview}")
                
                content.append("")
                
            except Exception as e:
                content.append(f"   Error displaying result {i+1}: {str(e)}")
                content.append("")
        
        if len(successful_results) > display_count:
            remaining = len(successful_results) - display_count
            content.append(f"... and {remaining} more successful extractions.")
            content.append("")
        
        return content

    def _generate_failed_results_preview(self, failed_results):
        """Başarısız sonuçların önizlemesini oluştur"""
        content = [
            "FAILED EXTRACTIONS",
            "-" * 30
        ]
        
        display_count = min(5, len(failed_results))
        for i, result in enumerate(failed_results[:display_count]):
            try:
                url = result.get('url', 'Unknown URL')
                error = result.get('error', 'Unknown error')
                content.append(f"{i+1}. URL: {url}")
                content.append(f"   Error: {error}")
                content.append("")
            except Exception as e:
                content.append(f"   Error displaying failed result {i+1}: {str(e)}")
                content.append("")
        
        if len(failed_results) > display_count:
            remaining = len(failed_results) - display_count
            content.append(f"... and {remaining} more failed extractions.")
            content.append("")
        
        return content

    def _generate_duplicate_analysis(self, duplicate_results):
        """Duplicate analiz bölümünü oluştur"""
        content = [
            "DUPLICATE ANALYSIS",
            "-" * 50,
            ""
        ]

        # Duplicate'leri method'a göre grupla
        duplicates_by_method = {}
        for dup in duplicate_results:
            dup_info = dup.get('duplicate_info', {})
            method = dup_info.get('method', 'Unknown')
            if method not in duplicates_by_method:
                duplicates_by_method[method] = []
            duplicates_by_method[method].append(dup)

        for method, dups in duplicates_by_method.items():
            method_icon = "🧠" if method == "Embedding" else "🔍" if method == "MinHash" else "🔗"
            content.append(f"{method_icon} {method} Duplicates ({len(dups)}):")
            content.append("-" * 30)
            
            for i, dup in enumerate(dups[:5]):  # İlk 5'ini göster
                try:
                    url = dup.get('url', 'Unknown URL')
                    child_cat = dup.get('child_category', 'Unknown')
                
                    dup_info = dup.get('duplicate_info', {})
                    original_url = dup_info.get('original_url', 'Unknown')
                    similarity = dup_info.get('similarity', 0)

                    content.append(f"  {i+1}. URL: {url}")
                    content.append(f"     Category: {child_cat}")
                    content.append(f"     Similarity: {similarity:.3f}")
                    content.append(f"     Original: {original_url}")

                    # Tüm similarity skorlarını göster
                    similarity_scores = dup.get('similarity_scores', {})
                    if similarity_scores:
                        content.append("     All Scores:")
                        content.append(f"       MinHash: {similarity_scores.get('minhash_max_similarity', 0):.3f}")
                        content.append(f"       SimHash: {1 - similarity_scores.get('simhash_min_distance', 64)/64:.3f}")
                        if similarity_scores.get('embedding_enabled', False):
                            content.append(f"       Embedding: {similarity_scores.get('embedding_max_similarity', 0):.3f}")
                    
                    content.append("")

                except Exception as e:
                    content.append(f"     Error displaying duplicate {i+1}: {str(e)}")
                    content.append("")
            
            if len(dups) > 5:
                content.append(f"     ... and {len(dups) - 5} more {method} duplicates.")
            content.append("")

        return content

    def _format_duplicate_info(self, result):
        """Duplicate bilgilerini formatla"""
        content = []
        dup_info = result.get('duplicate_info', {})
        method = dup_info.get('method', 'Unknown')
        original_url = dup_info.get('original_url', 'Unknown')
        similarity = dup_info.get('similarity', 0)
        
        method_icon = "🧠" if method == "Embedding" else "🔍" if method == "MinHash" else "🔗"
        content.append(f"   🔄 DUPLICATE: {method_icon} {method} (similarity: {similarity:.3f})")
        content.append(f"      Original: {original_url}")

        # Detaylı similarity skorları
        similarity_scores = result.get('similarity_scores', {})
        if similarity_scores:
            content.append("      Similarity Scores:")
            content.append(f"        • MinHash: {similarity_scores.get('minhash_max_similarity', 0):.3f}")
            content.append(f"        • SimHash: {1 - similarity_scores.get('simhash_min_distance', 64)/64:.3f}")
            if similarity_scores.get('embedding_enabled', False):
                content.append(f"        • Embedding: {similarity_scores.get('embedding_max_similarity', 0):.3f}")
        
        return content

    def _create_buttons(self, button_frame, preview_window, on_confirm):
        """Preview window butonlarını oluştur"""
        def on_cancel():
            try:
                preview_window.destroy()
            except Exception as e:
                print(f"Error in cancel: {e}")

        def on_confirm_and_close():
            try:
                on_confirm()
                preview_window.destroy()
            except Exception as e:
                print(f"Error in confirm: {e}")
                messagebox.showerror("Error", f"Could not save results: {str(e)}")

        def export_logs():
            try:
                if hasattr(self.extractor, 'similarity_checker'):
                    filename = filedialog.asksaveasfilename(
                        title="Export Similarity Logs",
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                    )
                    if filename:
                        self.extractor.similarity_checker.export_similarity_logs(filename)
                        messagebox.showinfo("Export Complete", f"Similarity logs exported to {filename}")
                else:
                    messagebox.showwarning("Export Error", "Similarity checker not available")
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not export logs: {str(e)}")

        # Buttons
        export_btn = ttk.Button(button_frame, text="Export Similarity Logs", command=export_logs)
        export_btn.pack(side=tk.LEFT)

        cancel_btn = ttk.Button(button_frame, text="Cancel", style="Danger.TButton", command=on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=10)

        confirm_btn = ttk.Button(button_frame, text="Save Results", style="Success.TButton", 
                                command=on_confirm_and_close)
        confirm_btn.pack(side=tk.RIGHT)

    def _center_window(self, window):
        """Pencereyi ekranın ortasına getir"""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
        y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
        window.geometry(f"+{x}+{y}")

    def _handle_preview_error(self, error, on_confirm):
        """Preview hatası durumunda işlem yap"""
        error_msg = f"Error creating preview window: {str(error)}"
        print(error_msg)  # Debug için
        messagebox.showerror("Preview Error", error_msg)
        
        # Eğer preview açılamazsa direkt kaydetme seçeneği sun
        response = messagebox.askyesno("Save Without Preview", 
                                    "Could not show preview. Do you want to save the results anyway?")
        if response:
            try:
                on_confirm()
            except Exception as save_error:
                messagebox.showerror("Save Error", f"Could not save results: {str(save_error)}")