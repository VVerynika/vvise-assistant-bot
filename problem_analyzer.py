import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional
import re
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path

@dataclass
class Problem:
    id: str
    title: str
    description: str
    source: str  # 'slack', 'clickup', 'telegram'
    source_id: str
    channel_task: str
    user: str
    timestamp: datetime
    priority: int  # 1-5, где 1 - высший приоритет
    status: str  # 'new', 'in_progress', 'resolved', 'duplicate', 'related'
    category: str
    tags: List[str]
    related_problems: List[str]
    last_updated: datetime
    progress_notes: List[str]
    
    def to_dict(self):
        return asdict(self)

class ProblemAnalyzer:
    def __init__(self, db_path: str = "/workspace/problems.db"):
        self.db_path = db_path
        self.init_database()
        self.problem_patterns = self._load_problem_patterns()
        
    def _load_problem_patterns(self) -> Dict[str, List[str]]:
        """Загружает паттерны для определения проблем"""
        return {
            'bug': [
                r'баг', r'ошибка', r'не работает', r'сломалось', r'проблема',
                r'bug', r'error', r'broken', r'issue', r'problem'
            ],
            'feature_request': [
                r'нужно', r'хочу', r'добавить', r'сделать', r'функция',
                r'need', r'want', r'add', r'make', r'feature'
            ],
            'urgent': [
                r'срочно', r'критично', r'важно', r'немедленно',
                r'urgent', r'critical', r'important', r'immediately'
            ],
            'user_complaint': [
                r'жалоба', r'недоволен', r'плохо', r'ужасно',
                r'complaint', r'dissatisfied', r'bad', r'terrible'
            ]
        }
    
    def init_database(self):
        """Инициализирует базу данных для хранения проблем"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                channel_task TEXT,
                user TEXT,
                timestamp TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'new',
                category TEXT,
                tags TEXT,
                related_problems TEXT,
                last_updated TEXT NOT NULL,
                progress_notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problem_relations (
                problem_id TEXT,
                related_id TEXT,
                relation_type TEXT,
                confidence REAL,
                FOREIGN KEY (problem_id) REFERENCES problems (id),
                FOREIGN KEY (related_id) REFERENCES problems (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze_text(self, text: str) -> Dict[str, any]:
        """Анализирует текст и определяет тип проблемы, приоритет и категорию"""
        if not text:
            return {}
        
        text_lower = text.lower()
        analysis = {
            'category': 'general',
            'priority': 3,
            'tags': [],
            'urgency_score': 0
        }
        
        # Определяем категорию
        for category, patterns in self.problem_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    analysis['category'] = category
                    break
        
        # Определяем приоритет
        urgency_indicators = {
            'urgent': 5,
            'critical': 5,
            'important': 4,
            'bug': 4,
            'error': 4,
            'broken': 4
        }
        
        for indicator, priority in urgency_indicators.items():
            if indicator in text_lower:
                analysis['priority'] = min(analysis['priority'], priority)
                analysis['urgency_score'] += 1
        
        # Определяем теги
        for category, patterns in self.problem_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    analysis['tags'].append(category)
        
        # Убираем дубликаты тегов
        analysis['tags'] = list(set(analysis['tags']))
        
        return analysis
    
    def find_similar_problems(self, text: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Находит похожие проблемы в базе данных"""
        # Простая реализация поиска похожих проблем по ключевым словам
        # В реальной системе здесь можно использовать более сложные алгоритмы ML
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, description FROM problems')
        problems = cursor.fetchall()
        conn.close()
        
        similar = []
        text_words = set(re.findall(r'\w+', text.lower()))
        
        for problem_id, title, description in problems:
            problem_text = f"{title} {description}".lower()
            problem_words = set(re.findall(r'\w+', problem_text))
            
            if text_words and problem_words:
                intersection = len(text_words.intersection(problem_words))
                union = len(text_words.union(problem_words))
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= threshold:
                    similar.append((problem_id, similarity))
        
        # Сортируем по убыванию схожести
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar
    
    def add_problem(self, problem: Problem) -> str:
        """Добавляет новую проблему в базу данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем на дубликаты
        similar = self.find_similar_problems(f"{problem.title} {problem.description}")
        
        if similar and similar[0][1] > 0.8:
            # Высокая схожесть - помечаем как дубликат
            problem.status = 'duplicate'
            problem.related_problems = [similar[0][0]]
        elif similar and similar[0][1] > 0.6:
            # Средняя схожесть - помечаем как связанную
            problem.related_problems = [similar[0][0]]
        
        cursor.execute('''
            INSERT OR REPLACE INTO problems 
            (id, title, description, source, source_id, channel_task, user, 
             timestamp, priority, status, category, tags, related_problems, 
             last_updated, progress_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            problem.id,
            problem.title,
            problem.description,
            problem.source,
            problem.source_id,
            problem.channel_task,
            problem.user,
            problem.timestamp.isoformat(),
            problem.priority,
            problem.status,
            problem.category,
            json.dumps(problem.tags),
            json.dumps(problem.related_problems),
            problem.last_updated.isoformat(),
            json.dumps(problem.progress_notes)
        ))
        
        conn.commit()
        conn.close()
        
        return problem.id
    
    def update_problem_status(self, problem_id: str, status: str, progress_note: str = None):
        """Обновляет статус проблемы и добавляет заметку о прогрессе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if progress_note:
            cursor.execute('SELECT progress_notes FROM problems WHERE id = ?', (problem_id,))
            result = cursor.fetchone()
            if result:
                notes = json.loads(result[0]) if result[0] else []
                notes.append({
                    'timestamp': datetime.now().isoformat(),
                    'note': progress_note
                })
                
                cursor.execute('''
                    UPDATE problems 
                    SET status = ?, progress_notes = ?, last_updated = ?
                    WHERE id = ?
                ''', (status, json.dumps(notes), datetime.now().isoformat(), problem_id))
        
        conn.commit()
        conn.close()
    
    def get_problems_by_status(self, status: str = None) -> List[Problem]:
        """Получает проблемы по статусу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM problems WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM problems')
        
        rows = cursor.fetchall()
        conn.close()
        
        problems = []
        for row in rows:
            problem = Problem(
                id=row[0],
                title=row[1],
                description=row[2],
                source=row[3],
                source_id=row[4],
                channel_task=row[5],
                user=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                priority=row[8],
                status=row[9],
                category=row[10],
                tags=json.loads(row[11]) if row[11] else [],
                related_problems=json.loads(row[12]) if row[12] else [],
                last_updated=datetime.fromisoformat(row[13]),
                progress_notes=json.loads(row[14]) if row[14] else []
            )
            problems.append(problem)
        
        return problems
    
    def get_forgotten_problems(self, days_threshold: int = 7) -> List[Problem]:
        """Получает проблемы, по которым нет прогресса"""
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM problems 
            WHERE status IN ('new', 'in_progress') 
            AND last_updated < ?
            ORDER BY priority ASC, last_updated ASC
        ''', (threshold_date.isoformat(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        problems = []
        for row in rows:
            problem = Problem(
                id=row[0],
                title=row[1],
                description=row[2],
                source=row[3],
                source_id=row[4],
                channel_task=row[5],
                user=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                priority=row[8],
                status=row[9],
                category=row[10],
                tags=json.loads(row[11]) if row[11] else [],
                related_problems=json.loads(row[12]) if row[12] else [],
                last_updated=datetime.fromisoformat(row[13]),
                progress_notes=json.loads(row[14]) if row[14] else []
            )
            problems.append(problem)
        
        return problems
    
    def generate_report(self) -> Dict[str, any]:
        """Генерирует сводный отчет по всем проблемам"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM problems')
        total_problems = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE status = "new"')
        new_problems = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE status = "in_progress"')
        in_progress = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE status = "resolved"')
        resolved = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE status = "duplicate"')
        duplicates = cursor.fetchone()[0]
        
        # Проблемы по приоритету
        cursor.execute('SELECT priority, COUNT(*) FROM problems GROUP BY priority ORDER BY priority')
        priority_stats = dict(cursor.fetchall())
        
        # Проблемы по категории
        cursor.execute('SELECT category, COUNT(*) FROM problems GROUP BY category')
        category_stats = dict(cursor.fetchall())
        
        # Проблемы по источнику
        cursor.execute('SELECT source, COUNT(*) FROM problems GROUP BY source')
        source_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_problems': total_problems,
            'by_status': {
                'new': new_problems,
                'in_progress': in_progress,
                'resolved': resolved,
                'duplicate': duplicates
            },
            'by_priority': priority_stats,
            'by_category': category_stats,
            'by_source': source_stats,
            'generated_at': datetime.now().isoformat()
        }
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Очищает старые данные"""
        threshold_date = datetime.now() - timedelta(days=days_to_keep)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM problems WHERE last_updated < ?', (threshold_date.isoformat(),))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count