from goose3 import Goose
from goose3.configuration import Configuration
import time
import re
from urllib.parse import urlparse
import logging
from llm_classifier import LLMClassifier
from similarity_checker import SimilarityChecker  # Kategori olmayan versiyon

logger = logging.getLogger(__name__)

class URLExtractor:
    def __init__(self, timeout=10, delay=0.1):
        self.timeout = timeout
        self.delay = delay

        config = Configuration()
        config.request_timeout = timeout
        config.browser_user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        config.enable_image_fetching = False

        self.goose = Goose(config)
        
        # LLM classifier
        self.llm_classifier = LLMClassifier()

        # Similarity checker
        self.similarity_checker = SimilarityChecker()

    def __del__(self):
        try:
            self.goose.close()
        except:
            pass

    def is_valid_url(self, url):
        try:
            result = urlparse(url.strip())
            return all([result.scheme, result.netloc])
        except:
            return False

    def clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


    def extract_content(self, url):
        result = {
            'url': url,
            'title': '',
            'content': '',
            'status': 'failed',
            'error': '',
            'child_category': '',
            'parent_category': '',
            'summary': '',
            'is_duplicate': False,
            'duplicate_info': {},
            'similarity_scores': {
                'minhash_max_similarity': 0.0,
                'simhash_min_distance': 64,
                'embedding_max_similarity': 0.0,
                'embedding_enabled': False
            }
        }

        try:
            if not self.is_valid_url(url):
                result['error'] = 'Invalid URL format'
                return result

            article = self.goose.extract(url=url)
            result['title'] = self.clean_text(article.title or '')
            result['content'] = self.clean_text(article.cleaned_text or '')

            if not result['content'] and not result['title']:
                result['error'] = 'No content extracted'
                return result        
            
            result['status'] = 'success'

            # Duplicate kontrolü LLM'den önce yapılır
            is_duplicate, duplicate_info, similarity_scores = self.similarity_checker.is_duplicate_comprehensive(
                url, result['title'], result['content']
            )

            result['is_duplicate'] = is_duplicate
            result['similarity_scores'] = similarity_scores
            
            # Backward compatibility için ayrı alanlar
            result['minhash_similarity'] = similarity_scores['minhash_max_similarity']
            result['simhash_distance'] = similarity_scores['simhash_min_distance']
            result['embedding_similarity'] = similarity_scores['embedding_max_similarity']

            # Eğer duplicate ise, varsa cache'ten summary ve category çek
            if is_duplicate and duplicate_info:
                result['duplicate_info'] = duplicate_info
                cached = self.similarity_checker.get_cached_llm_output(duplicate_info['original_url'])
                if cached:
                    result['summary'] = cached.get("summary", "")
                    result['child_category'] = cached.get("category", "")
                else:
                    result['summary'] = "(no summary cached)"
                    result['child_category'] = "(unknown)"
            else:
                # LLM çağrısı (özeti ve kategoriyi çıkar)
                llm_output = self.llm_classifier.classify_text(result['title'], result['content'])
                result['child_category'] = llm_output.get("category", "Unknown")
                result['summary'] = llm_output.get("summary", "")

                # LLM sonucu cache'e ekle
                self.similarity_checker.cache_llm_output(url, {
                    "summary": result['summary'],
                    "category": result['child_category']
                })

        except Exception as e:
            error_msg = str(e).lower()
            if 'timeout' in error_msg:
                result['error'] = 'Timeout error'
            elif 'connection' in error_msg:
                result['error'] = 'Connection error'
            elif any(code in error_msg for code in ['404', '403', '500', '502', '503']):
                result['error'] = f'HTTP error: {error_msg}'
            else:
                result['error'] = f'Unexpected error: {str(e)}'

        return result

    def extract_multiple_urls(self, urls, progress_callback=None, stop_flag=None):
        results = []
        total_urls = len(urls)
        start_time = time.time()

        for i, url in enumerate(urls):
            if stop_flag and stop_flag():
                break

            if progress_callback:
                progress = (i + 1) / total_urls * 100
                progress_callback(progress, f"Processing URL {i+1}/{total_urls}: {url.strip()}")

            result = self.extract_content(url.strip())
            results.append(result)

            if progress_callback:
                status_msg = ""
                if result['status'] == 'success':
                    if result.get('is_duplicate', False):
                        method = result.get("duplicate_info", {}).get("method", "Unknown")
                        original_url = result.get("duplicate_info", {}).get("original_url", "N/A")
                        similarity_info = (
                            f"MinHash: {result.get('minhash_similarity', 0):.3f} | "
                            f"SimHash: {result.get('simhash_distance', 64)}"
                        )
                        # Embedding varsa ekle
                        if result.get('similarity_scores', {}).get('embedding_enabled', False):
                            emb_sim = result['similarity_scores'].get('embedding_max_similarity', 0)
                            similarity_info += f" | Embedding: {emb_sim:.3f}"
                        status_msg = f"🔄 DUPLICATE ({method}) → {original_url} | {similarity_info}"
                    else:
                        similarity_info = (
                            f"MinHash: {result.get('minhash_similarity', 0):.3f} | "
                            f"SimHash: {result.get('simhash_distance', 64)}"
                        )
                        if result.get('similarity_scores', {}).get('embedding_enabled', False):
                            emb_sim = result['similarity_scores'].get('embedding_max_similarity', 0)
                            similarity_info += f" | Embedding: {emb_sim:.3f}"

                        status_msg = f"✅ Success | Category: {result.get('child_category', 'Unknown')} | {similarity_info}"
                elif result['status'] == 'failed':
                    error = result.get('error', 'Unknown error')
                    status_msg = f"❌ Failed ({error})"
                else:
                    status_msg = f"Status: {result['status']}"

                progress_callback(progress, status_msg)

            if i < total_urls - 1:
                time.sleep(getattr(self, 'delay', 0))

        return results



    def get_similarity_analysis(self):
        return self.similarity_checker.analyze_similarity_distribution()
    def get_similarity_stats(self):
        """Get comprehensive similarity statistics"""
        try:
            if hasattr(self, 'similarity_checker'):
                return self.similarity_checker.get_comprehensive_stats()
            return None
        except Exception as e:
            print(f"Error getting similarity stats: {e}")
            return None