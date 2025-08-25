import csv
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class FileHandler:
    """Dosya okuma ve yazma işlemleri için sınıf"""
    
    def __init__(self):
        pass
    
    def read_urls_from_txt(self, file_path: str) -> List[str]:
        """
        TXT dosyasından URL'leri oku
        
        Args:
            file_path (str): TXT dosya yolu
            
        Returns:
            List[str]: URL'lerin listesi
            
        Raises:
            FileNotFoundError: Dosya bulunamazsa
            Exception: Diğer okuma hataları
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            urls = []
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    
                    # Boş satırları atla
                    if not line:
                        continue
                    
                    # Yorum satırlarını atla (# ile başlayanlar)
                    if line.startswith('#'):
                        continue
                    
                    urls.append(line)
                    logger.debug(f"Read URL from line {line_num}: {line}")
            
            logger.info(f"Successfully read {len(urls)} URLs from {file_path}")
            return urls
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading file {file_path}: {e}")
            raise Exception(f"File encoding error: {e}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise Exception(f"File reading error: {e}")
    
    def validate_txt_file(self, file_path: str) -> Dict[str, any]:
        """
        TXT dosyasını doğrula
        
        Args:
            file_path (str): TXT dosya yolu
            
        Returns:
            Dict: Doğrulama sonuçları
        """
        result = {
            'valid': False,
            'url_count': 0,
            'errors': []
        }
        
        try:
            if not os.path.exists(file_path):
                result['errors'].append("File does not exist")
                return result
            
            if not file_path.lower().endswith('.txt'):
                result['errors'].append("File is not a .txt file")
                return result
            
            # Dosya boyutu kontrolü (çok büyük dosyalar için)
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                result['errors'].append("File is too large (>10MB)")
                return result
            
            # URL'leri oku ve say
            urls = self.read_urls_from_txt(file_path)
            result['url_count'] = len(urls)
            
            if result['url_count'] == 0:
                result['errors'].append("No URLs found in file")
                return result
            
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def write_results_to_csv(self, results: List[Dict], output_path: str, append: bool = False):
        mode = 'a' if append else 'w'
        file_exists = os.path.exists(output_path)
        
        try:
            fieldnames = [
                'url', 'title', 'content', 'category', 'summary',
                'minhash_score', 'simhash_score', 'embedding_score',
                'is_duplicate', 'duplicate_of'
            ]
            
            with open(output_path, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=fieldnames,
                    quoting=csv.QUOTE_ALL,       # Tüm hücreleri tırnak içine al
                    quotechar='"',               # Tırnak karakteri
                    escapechar='\\',             # İçteki tırnakları kaçır
                    delimiter=','
                )
                
                if not append or not file_exists:
                    writer.writeheader()
                
                for result in results:
                    # minhash_similarity için güvenli alma ve dönüştürme
                    minhash_sim = result.get('minhash_similarity')
                    if minhash_sim is None:
                        minhash_sim = ''
                    
                    # embedding_score için güvenli alma ve dönüştürme
                    embedding_score = result.get('embedding_similarity')
                    if embedding_score is None:
                        embedding_score = ''
                    
                    # simhash_distance'ı simhash_score'a dönüştürme
                    simhash_dist = result.get('simhash_distance')
                    if isinstance(simhash_dist, (int, float)):
                        simhash_score = 1 - (simhash_dist / 64)
                    else:
                        simhash_score = ''
                    
                    # Category'yi child_category'den al
                    category = result.get('child_category', '')
                    
                    row = {
                        'url': result.get('url', ''),
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'category': category,
                        'summary': result.get('summary', ''),
                        'minhash_score': minhash_sim,
                        'simhash_score': simhash_score,
                        'embedding_score': embedding_score,
                        'is_duplicate': result.get('is_duplicate', False),
                        'duplicate_of': result.get('duplicate_info', {}).get('original_url', '')
                    }
                    
                    # İçeride özel karakter varsa temizle
                    for key in row:
                        if isinstance(row[key], str):
                            row[key] = row[key].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').strip()
                    
                    writer.writerow(row)
            
            print(f"Successfully wrote {len(results)} results to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error writing CSV file {output_path}: {e}")
            raise

    def write_summary_report(self, results: List[Dict], similarity_stats: Dict, output_path: str) -> bool:
        """
        Detaylı özet raporu oluştur
        """
        try:
            report_path = output_path.replace('.csv', '_summary_report.txt')
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("URL EXTRACTION SUMMARY REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                # Genel istatistikler
                total_urls = len(results)
                successful_urls = len([r for r in results if r['status'] == 'success'])
                failed_urls = total_urls - successful_urls
                
                f.write(f"GENERAL STATISTICS:\n")
                f.write(f"Total URLs processed: {total_urls}\n")
                f.write(f"Successful extractions: {successful_urls}\n")
                f.write(f"Failed extractions: {failed_urls}\n")
                f.write(f"Success rate: {(successful_urls/total_urls)*100:.1f}%\n\n")
                
                # Similarity statistics
                f.write(f"SIMILARITY ANALYSIS:\n")
                f.write(f"Unique content: {similarity_stats.get('unique_count', 0)}\n")
                f.write(f"Duplicate content: {similarity_stats.get('duplicate_count', 0)}\n")
                f.write(f"Total processed: {similarity_stats.get('total_processed', 0)}\n\n")
                
                # Parent kategori istatistikleri
                f.write(f"CONTENT BY PARENT CATEGORY:\n")
                category_stats = similarity_stats.get('category_stats', {})
                for category, count in sorted(category_stats.items()):
                    f.write(f"  {category}: {count} unique URLs\n")
                f.write("\n")
                
                # Hata analizi
                error_counts = {}
                for result in results:
                    if result['status'] == 'failed' and result['error']:
                        error_type = result['error']
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
                
                if error_counts:
                    f.write(f"ERROR ANALYSIS:\n")
                    for error_type, count in sorted(error_counts.items()):
                        f.write(f"  {error_type}: {count} occurrences\n")
                    f.write("\n")
                
                # Duplicate'ler
                duplicates = [r for r in results if r.get('is_duplicate')]
                if duplicates:
                    f.write(f"DUPLICATE CONTENT FOUND:\n")
                    for dup in duplicates:
                        f.write(f"  URL: {dup['url']}\n")
                        f.write(f"  Original: {dup['duplicate_of']}\n")
                        f.write(f"  Category: {dup['parent_category']}\n")
                        f.write(f"  Hash: {dup['content_hash'][:16]}...\n\n")
            
            print(f"Summary report saved to: {report_path}")
            return True
            
        except Exception as e:
            print(f"Error writing summary report: {e}")
            return False
    
    def create_sample_txt_file(self, file_path: str, sample_urls: List[str] = None) -> bool:
        """
        Örnek TXT dosyası oluştur (test amaçlı)
        
        Args:
            file_path (str): Oluşturulacak dosya yolu
            sample_urls (List[str]): Örnek URL'ler (varsayılan listesi var)
            
        Returns:
            bool: Başarı durumu
        """
        if sample_urls is None:
            sample_urls = [
                "# Sample URLs for testing",
                "https://www.example.com",
                "https://httpbin.org/html",
                "https://www.github.com",
                "https://www.stackoverflow.com",
                "",
                "# Add more URLs below:",
                "https://www.wikipedia.org"
            ]
        
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                for url in sample_urls:
                    file.write(url + '\n')
            
            logger.info(f"Sample TXT file created: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sample file {file_path}: {e}")
            return False
