import re
import json
import numpy as np
from datasketch import MinHash, MinHashLSH
from simhash import Simhash
from collections import defaultdict
from typing import Dict, Tuple, List, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging

class SimilarityChecker:
    ENGLISH_STOPWORDS = {
            "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "by", "for",
            "with", "about", "as", "to", "from", "of", "that", "this", "is", "was",
            "are", "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "i", "you", "he", "she", "it", "we", "they"
        }
    
    def __init__(self, threshold_minhash=0.35, threshold_simhash=16, threshold_embedding=0.8, 
        embedding_model_name='all-MiniLM-L6-v2',embedding_enabled = True):
        self.minhash_lsh = MinHashLSH(threshold=threshold_minhash)
        self.minhash_storage = {}
        self.simhash_storage = {}
        self.embedding_storage = {}
        self.llm_cache = {}
        self.embedding_enabled = embedding_enabled

        self.threshold_minhash = threshold_minhash
        self.threshold_simhash = threshold_simhash
        self.threshold_embedding = threshold_embedding

        # embedding_enabled kaldırıldı, embedding modeli kesin yükleniyor
        try:
            self.embedding_model = SentenceTransformer(embedding_model_name)
            logging.info(f"Embedding model '{embedding_model_name}' loaded successfully")
        except Exception as e:
            logging.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None

        self.duplicate_stats = {
            'total_duplicates': 0,
            'detection_methods': defaultdict(int),
            'category_stats': defaultdict(int)
        }

        self.similarity_logs = []


    def clean_text(self, text, remove_stopwords=False):
        """Daha yumuşak metin temizleme"""
        if not text:
            return ""
        
        # HTML etiketlerini temizle
        text = re.sub(r'<[^>]+>', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Küçük harfe çevir
        text = text.lower().strip()
        
        # Sadece aşırı özel karakterleri temizle, noktalama işaretlerini koru
        text = re.sub(r'[^\w\s\.\,\!\?]', '', text)

        if remove_stopwords:
            words = [w for w in text.split() if w not in self.ENGLISH_STOPWORDS]
            text = ' '.join(words)

        return text


    def create_minhash(self, content, num_perm=128):
        cleaned_text = self.clean_text(content, remove_stopwords=True)
        words = cleaned_text.split()

        tokens = set()
        tokens.update(words)

        for i in range(len(words) - 1):
            tokens.add(f"{words[i]} {words[i+1]}")
        if len(words) > 10:
            for i in range(len(words) - 2):
                tokens.add(f"{words[i]} {words[i+1]} {words[i+2]}")

        clean_no_space = cleaned_text.replace(' ', '')
        for i in range(len(clean_no_space) - 3):
            tokens.add(clean_no_space[i:i+4])

        minhash = MinHash(num_perm=num_perm)
        for token in tokens:
            minhash.update(token.encode('utf-8'))
        return minhash


    def create_simhash(self, content):
        cleaned_text = self.clean_text(content, remove_stopwords=True)
        return Simhash(cleaned_text)
    
    def create_embedding(self, content):
        if self.embedding_model is None:
            return None
        try:
            cleaned_text = self.clean_text(content,remove_stopwords=False)
            if len(cleaned_text) > 5000:
                cleaned_text = cleaned_text[:5000]
            embedding = self.embedding_model.encode(cleaned_text)
            return embedding
        except Exception as e:
            logging.error(f"Failed to create embedding: {e}")
            return None


    def calculate_embedding_similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings"""
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        try:
            # Reshape for sklearn
            emb1 = embedding1.reshape(1, -1)
            emb2 = embedding2.reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            logging.error(f"Failed to calculate embedding similarity: {e}")
            return 0.0

    def is_duplicate(self, url, content):
        """Basit duplicate kontrolü - backward compatibility"""
        result = self.is_duplicate_comprehensive(url, "", content)
        return result[0], result[1].get('original_url'), result[1].get('method'), result[1].get('similarity', 0.0)

    def is_duplicate_comprehensive(self, url, title, content) -> Tuple[bool, Dict, Dict]:
        combined_text = f"{title} {content}"
        minhash = self.create_minhash(combined_text)
        simhash = self.create_simhash(combined_text)
        embedding = self.create_embedding(combined_text)

        similarity_scores = {
            'minhash_max_similarity': 0.0,
            'simhash_min_distance': 64,
            'embedding_max_similarity': 0.0,
            'embedding_enabled': True  # embed hep aktif artık
        }

        best_minhash_similarity = 0
        best_minhash_url = None
        for stored_url, stored_minhash in self.minhash_storage.items():
            similarity = minhash.jaccard(stored_minhash)
            if similarity > best_minhash_similarity:
                best_minhash_similarity = similarity
                best_minhash_url = stored_url

        similarity_scores['minhash_max_similarity'] = best_minhash_similarity

        best_simhash_distance = 64
        best_simhash_url = None
        for stored_url, stored_simhash in self.simhash_storage.items():
            distance = simhash.distance(stored_simhash)
            if distance < best_simhash_distance:
                best_simhash_distance = distance
                best_simhash_url = stored_url

        similarity_scores['simhash_min_distance'] = best_simhash_distance

        best_embedding_similarity = 0
        best_embedding_url = None
        if embedding is not None:
            for stored_url, stored_embedding in self.embedding_storage.items():
                similarity = self.calculate_embedding_similarity(embedding, stored_embedding)
                if similarity > best_embedding_similarity:
                    best_embedding_similarity = similarity
                    best_embedding_url = stored_url

        similarity_scores['embedding_max_similarity'] = best_embedding_similarity

        self.log_similarity_scores(url, similarity_scores, title, content)

        duplicate_info = {}
        is_duplicate = False

        if best_embedding_similarity >= self.threshold_embedding:
            is_duplicate = True
            duplicate_info = {
                'method': 'Embedding',
                'original_url': best_embedding_url,
                'similarity': best_embedding_similarity
            }
            self.duplicate_stats['total_duplicates'] += 1
            self.duplicate_stats['detection_methods']['Embedding'] += 1

        elif best_minhash_similarity >= self.threshold_minhash:
            is_duplicate = True
            duplicate_info = {
                'method': 'MinHash',
                'original_url': best_minhash_url,
                'similarity': best_minhash_similarity
            }
            self.duplicate_stats['total_duplicates'] += 1
            self.duplicate_stats['detection_methods']['MinHash'] += 1

        elif best_simhash_distance <= self.threshold_simhash:
            is_duplicate = True
            simhash_similarity = 1 - best_simhash_distance / 64
            duplicate_info = {
                'method': 'SimHash',
                'original_url': best_simhash_url,
                'similarity': simhash_similarity
            }
            self.duplicate_stats['total_duplicates'] += 1
            self.duplicate_stats['detection_methods']['SimHash'] += 1

        if not is_duplicate:
            self.minhash_storage[url] = minhash
            self.simhash_storage[url] = simhash
            self.minhash_lsh.insert(url, minhash)
            if embedding is not None:
                self.embedding_storage[url] = embedding

        return is_duplicate, duplicate_info, similarity_scores


    def log_similarity_scores(self, url, similarity_scores, title, content):
        log_entry = {
            'url': url,
            'title': title[:100],
            'content_length': len(content),
            'timestamp': np.datetime64('now'),
            'scores': similarity_scores.copy()
        }
        self.similarity_logs.append(log_entry)
        logging.info(f"Similarity check for {url}: "
                    f"MinHash={similarity_scores['minhash_max_similarity']:.3f}, "
                    f"SimHash={1 - similarity_scores['simhash_min_distance']/64:.3f}, "
                    f"Embedding={similarity_scores['embedding_max_similarity']:.3f}")


    def debug_similarity_scores(self, url, title, content):
        """Debug için benzerlik skorlarını göster"""
        combined_text = f"{title} {content}"
        minhash = self.create_minhash(combined_text)
        simhash = self.create_simhash(combined_text)
        embedding = self.create_embedding(combined_text)
        
        print(f"\n=== Debug for {url} ===")
        print(f"Text length: {len(combined_text)}")
        print(f"Cleaned text preview: {self.clean_text(combined_text)[:200]}...")
        print(f"Embedding enabled: {self.embedding_enabled}")
        
        print(f"\nSimilarity scores with existing {len(self.minhash_storage)} documents:")
        
        for stored_url, stored_minhash in self.minhash_storage.items():
            minhash_sim = minhash.jaccard(stored_minhash)
            simhash_dist = simhash.distance(self.simhash_storage[stored_url])
            simhash_sim = 1 - simhash_dist / 64
            
            embedding_sim = 0.0
            if self.embedding_enabled and embedding is not None and stored_url in self.embedding_storage:
                embedding_sim = self.calculate_embedding_similarity(embedding, self.embedding_storage[stored_url])
            
            print(f"  vs {stored_url[:50]}...")
            print(f"    MinHash: {minhash_sim:.3f} (threshold: {self.threshold_minhash})")
            print(f"    SimHash: {simhash_sim:.3f} (distance: {simhash_dist}, threshold: {self.threshold_simhash})")
            print(f"    Embedding: {embedding_sim:.3f} (threshold: {self.threshold_embedding})")
            print()

    def get_similarity_logs(self, limit: Optional[int] = None) -> List[Dict]:
        """Get similarity logs for analysis"""
        if limit:
            return self.similarity_logs[-limit:]
        return self.similarity_logs

    def export_similarity_logs(self, filename: str):
        """Export similarity logs to file"""
        
        
        # Convert numpy datetime to string for JSON serialization
        logs_for_export = []
        for log in self.similarity_logs:
            log_copy = log.copy()
            if 'timestamp' in log_copy:
                log_copy['timestamp'] = str(log_copy['timestamp'])
            logs_for_export.append(log_copy)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(logs_for_export, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Similarity logs exported to {filename}")

    def cache_llm_output(self, url, llm_data):
        """Cache LLM output data"""
        self.llm_cache[url] = llm_data
        
        # Update category statistics
        if isinstance(llm_data, dict) and 'category' in llm_data:
            category = llm_data['category']
            self.duplicate_stats['category_stats'][category] += 1

    def get_cached_llm_output(self, url):
        """Get cached LLM output for a URL"""
        return self.llm_cache.get(url, None)

    def get_comprehensive_stats(self):
        """Get comprehensive statistics about similarity detection"""
        unique_count = len(self.minhash_storage)
        total_duplicates = self.duplicate_stats['total_duplicates']
        
        return {
            'unique_count': unique_count,
            'total_duplicates': total_duplicates,
            'total_processed': unique_count + total_duplicates,
            'detection_methods': dict(self.duplicate_stats['detection_methods']),
            'category_stats': dict(self.duplicate_stats['category_stats']),
            'duplicate_rate': total_duplicates / (unique_count + total_duplicates) if (unique_count + total_duplicates) > 0 else 0,
            'embedding_enabled': self.embedding_enabled,
            'embedding_count': len(self.embedding_storage),
            'similarity_logs_count': len(self.similarity_logs)
        }

    def analyze_similarity_distribution(self):
        """Analyze the distribution of similarity scores"""
        minhash_similarities = []
        simhash_distances = []
        embedding_similarities = []
        
        # Calculate all pairwise similarities (for analysis)
        urls = list(self.minhash_storage.keys())
        for i, url1 in enumerate(urls):
            for j, url2 in enumerate(urls[i+1:], i+1):
                minhash1 = self.minhash_storage[url1]
                minhash2 = self.minhash_storage[url2]
                simhash1 = self.simhash_storage[url1]
                simhash2 = self.simhash_storage[url2]
                
                minhash_sim = minhash1.jaccard(minhash2)
                simhash_dist = simhash1.distance(simhash2)
                
                minhash_similarities.append(minhash_sim)
                simhash_distances.append(simhash_dist)
                
                # Calculate embedding similarity if available
                if (self.embedding_enabled and 
                    url1 in self.embedding_storage and 
                    url2 in self.embedding_storage):
                    embedding1 = self.embedding_storage[url1]
                    embedding2 = self.embedding_storage[url2]
                    embedding_sim = self.calculate_embedding_similarity(embedding1, embedding2)
                    embedding_similarities.append(embedding_sim)
        
        result = {
            'minhash_stats': self._calculate_stats(minhash_similarities),
            'simhash_stats': self._calculate_stats(simhash_distances),
            'embedding_stats': self._calculate_stats(embedding_similarities) if embedding_similarities else {'count': 0, 'avg': 0, 'max': 0, 'min': 0}
        }
        
        return result

    def _calculate_stats(self, values):
        """Helper function to calculate statistics"""
        if not values:
            return {'count': 0, 'avg': 0, 'max': 0, 'min': 0}
        
        return {
            'count': len(values),
            'avg': sum(values) / len(values),
            'max': max(values),
            'min': min(values)
        }

    def reset_stats(self):
        """Reset all statistics"""
        self.duplicate_stats = {
            'total_duplicates': 0,
            'detection_methods': defaultdict(int),
            'category_stats': defaultdict(int)
        }
        self.similarity_logs = []

    def get_embedding_model_info(self):
        """Get information about the embedding model"""
        if not self.embedding_enabled:
            return {"enabled": False, "model": None, "error": "Model not loaded"}
        
        try:
            model_info = {
                "enabled": True,
                "model_name": self.embedding_model.get_model_name() if hasattr(self.embedding_model, 'get_model_name') else "Unknown",
                "max_seq_length": getattr(self.embedding_model, 'max_seq_length', 'Unknown'),
                "embedding_dimension": self.embedding_model.get_sentence_embedding_dimension() if hasattr(self.embedding_model, 'get_sentence_embedding_dimension') else 'Unknown'
            }
            return model_info
        except Exception as e:
            return {"enabled": True, "model": "Loaded but info unavailable", "error": str(e)}