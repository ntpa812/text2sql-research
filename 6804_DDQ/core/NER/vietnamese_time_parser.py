# Vietnamese Time Parser - Inference Ready Class
import re
import datetime
from calendar import monthrange
import dateparser
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple

class VietnameseTimeParser:
    """
    A comprehensive Vietnamese time parser for converting natural language time expressions
    to date ranges. Supports various Vietnamese time formats including:
    - Relative times (e.g., '3 ngày trước', '2 tuần qua')
    - Specific dates (e.g., 'ngày 15/12/2024', 'ngày 30 tháng 1 năm ngoái')
    - Period references (e.g., 'đầu tháng', 'cuối năm', 'quý này')
    - Date ranges (e.g., 'từ 01/01 đến 31/12')
    """
    
    def __init__(self, current_date: Optional[datetime.datetime] = None):
        """
        Initialize the parser with optional current date (defaults to today).
        
        Args:
            current_date: Reference date for relative time calculations (defaults to now)
        """
        self.TODAY = current_date or datetime.datetime.now()
        self.CURRENT_YEAR = self.TODAY.year
        
        self.VI_NUMBER_MAP = {
            "một": 1,
            "hai": 2,
            "ba": 3,
            "bốn": 4,
            "sáu": 6,
            "bảy": 7,
            "tám": 8,
            "chín": 9,
            "mười": 10
        }
        
        self.TIME_UNITS = r"(ngày|tuần|tháng|năm)"
    
    def parse(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse Vietnamese time expression and return date range.
        
        Args:
            text: Vietnamese time expression (e.g., '3 ngày trước', 'tháng này')
            
        Returns:
            Tuple of (start_date, end_date) in 'YYYY-MM-DD' format, or (None, None) if parsing fails
        """
        text = self._normalize_vi_numbers(text)
        text = text.strip()
        
        # Try different parsing strategies in order
        for parser_func in [
            self._parse_range_explicit,
            self._parse_relative_range,
            self._parse_from_open
        ]:
            result = parser_func(text)
            if result:
                return self._format_date(result[0]), self._format_date(result[1])
        
        # Final fallback: leaf range parser
        result = self._parse_leaf_range(text)
        if result:
            return self._format_date(result[0]), self._format_date(result[1])
        
        return None, None
    
    # ==================== UTILITY METHODS ====================
    
    def _format_date(self, d: datetime.datetime) -> str:
        """Format datetime object to YYYY-MM-DD string."""
        return d.strftime('%Y-%m-%d')
    
    def _parse_date_basic(self, text: str) -> Optional[datetime.datetime]:
        """Parse date using dateparser library with Vietnamese settings."""
        return dateparser.parse(text, languages=['vi'], settings={
            'DATE_ORDER': 'DMY',
            'PREFER_DAY_OF_MONTH': 'first',
            'PREFER_DATES_FROM': 'current_period'
        })
    
    def _normalize_vi_numbers(self, text: str) -> str:
        """Convert Vietnamese number words to digits when followed by time units."""
        text = text.lower()
        for word, num in self.VI_NUMBER_MAP.items():
            pattern = rf'\b({word})\s+{self.TIME_UNITS}\b'
            text = re.sub(pattern, rf'{num} \2', text)
        return text
    
    def _resolve_year_modifier(self, modifier: Optional[str]) -> int:
        """Resolve year from modifier like 'nay', 'ngoái', 'trước', 'sau', 'kia', or explicit year."""
        year = self.CURRENT_YEAR
        if modifier:
            if modifier.isdigit():
                year = int(modifier)
            elif modifier in ['nay', 'này']:
                year = self.CURRENT_YEAR
            elif modifier in ['ngoái', 'trước']:
                year = self.CURRENT_YEAR - 1
            elif modifier == 'kia':
                year = self.CURRENT_YEAR - 2
            elif modifier == 'sau':
                year = self.CURRENT_YEAR + 1
        return year
    
    # ==================== LEAF RANGE PARSER ====================
    
    def _parse_leaf_range(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse simple time expressions without range operators."""
        text = text.strip().lower()
        
        # Today / now
        if text in ['nay', 'hôm nay', 'hiện tại', 'bây giờ']:
            return self.TODAY, self.TODAY
        
        # Weekdays (e.g., 'thứ năm tuần trước', 'chủ nhật')
        wd_match = re.search(r"\b(?:(chủ\s*nhật)|thứ\s*(hai|ba|bốn|tư|năm|sáu|bảy|[2-7]))(?:\s+tuần(?:\s+(nay|này|trước|ngoái|sau))?)?\b", text)
        if wd_match:
            result = self._parse_weekday(wd_match)
            if result:
                return result
        
        # Start of year (đầu năm)
        match = re.search(r'\bđầu\s+năm(?:\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?', text)
        if match:
            year = self._resolve_year_modifier(match.group(1))
            start = datetime.datetime(year, 1, 1)
            end = datetime.datetime(year, 1, 10)
            return start, end
        
        # End of year (cuối năm)
        match = re.search(r'cuối\s+năm(?:\s+(?:(\d{4})|(nay|này|ngoái|trước|sau|kia)))?', text)
        if match:
            return self._parse_end_of_year(match)
        
        # Last N days of month
        m_last_n = re.search(r'(?:tính\s+)?t(?:ừ|ừ\s+ngày)\s*(?:ngày\s*)?(?:cuối|cuối\s+cuùng|cuối\s+cùng|cuối\s+lúc|cuối\s+cùng|cuối\s+cuối|cuối\s+cuối cùng|cuối\s+cuối)?\s*(?:của\s+)?tháng(?:\s+(này|nay|ngoái|trước|sau))?(?:[^\d\n\r]*)?(?:về\s*)?(\d+)\s*ngày(?:\s+trước)?', text)
        if m_last_n:
            return self._parse_last_n_days_of_month(m_last_n)
        
        # Half of month (nửa đầu/cuối tháng)
        result = self._parse_half_month(text)
        if result:
            return result
        
        # Middle of month (giữa tháng)
        m_mid_month = re.search(r'giữa\s+tháng(?:\s+(1[0-2]|[1-9]))?(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?(?:\s*(này|nay|ngoái|trước|sau))?', text)
        if m_mid_month:
            return self._parse_middle_of_month(m_mid_month)
        
        # End of month (cuối tháng)
        m_end_month = re.search(r'cuối\s+tháng(?:\s+(1[0-2]|[1-9]))?(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?(?:\s*(này|nay|ngoái|trước|sau))?', text)
        if m_end_month:
            return self._parse_end_of_month(m_end_month)
        
        # Start of month (đầu tháng)
        match = re.search(r'(?<!nửa\s)đầu\s+tháng(?:\s+(1[0-2]|[1-9]))?(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?', text)
        if match:
            return self._parse_start_of_month(match, text)
        
        # Day before yesterday (hôm kia)
        if text in ["hôm kia", "ngày hôm kia", "ngày kia"]:
            d = self.TODAY - datetime.timedelta(days=2)
            return d, d
        
        # Quarter expressions
        result = self._parse_quarter(text)
        if result:
            return result
        
        # Specific date: ngày X tháng Y năm Z/ngoái/kia
        result = self._parse_specific_date(text)
        if result:
            return result
        
        # Month expressions
        result = self._parse_month(text)
        if result:
            return result
        
        # Year expressions
        result = self._parse_year(text)
        if result:
            return result
        
        # Week expressions
        result = self._parse_week(text)
        if result:
            return result
        
        # Fallback: single date
        d = self._parse_date_basic(text)
        if d:
            return d, d
        
        return None
    
    # ==================== SPECIFIC PARSERS ====================
    
    def _parse_weekday(self, match) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse weekday expressions like 'thứ năm tuần trước'."""
        sunday = match.group(1)
        word = match.group(2)
        mod = match.group(3)
        
        if sunday:
            weekday_idx = 6
        else:
            if re.fullmatch(r'[2-7]', word):
                weekday_idx = int(word) - 2
            else:
                wmap = {'hai': 0, 'ba': 1, 'bốn': 2, 'tư': 2, 'năm': 3, 'sáu': 4, 'bảy': 5}
                weekday_idx = wmap.get(word, 0)
        
        ref = self.TODAY
        if mod in ['trước', 'ngoái']:
            ref = self.TODAY - datetime.timedelta(weeks=1)
        elif mod == 'sau':
            ref = self.TODAY + datetime.timedelta(weeks=1)
        
        week_start = ref - datetime.timedelta(days=ref.weekday())
        d = week_start + datetime.timedelta(days=weekday_idx)
        return d, d
    
    def _parse_end_of_year(self, match) -> Tuple[datetime.datetime, datetime.datetime]:
        """Parse 'cuối năm' expressions."""
        y_digit = match.group(1)
        mod = match.group(2)
        year = self.CURRENT_YEAR
        
        if y_digit:
            year = int(y_digit)
            return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
        
        if mod in ['ngoái', 'trước']:
            year = self.CURRENT_YEAR - 1
        elif mod == 'kia':
            year = self.CURRENT_YEAR - 2
        elif mod == 'sau':
            year = self.CURRENT_YEAR + 1
        
        ld = monthrange(year, 12)[1]
        end = datetime.datetime(year, 12, ld)
        start_day = max(1, ld - 10)
        start = datetime.datetime(year, 12, start_day)
        return start, end
    
    def _parse_last_n_days_of_month(self, match) -> Tuple[datetime.datetime, datetime.datetime]:
        """Parse expressions like 'từ ngày cuối cùng của tháng về 10 ngày trước'."""
        mod = match.group(1)
        n_raw = match.group(2)
        try:
            n = int(n_raw)
        except Exception:
            n = 10
        
        if mod in ['trước', 'ngoái']:
            ref = self.TODAY - relativedelta(months=1)
        elif mod == 'sau':
            ref = self.TODAY + relativedelta(months=1)
        else:
            ref = self.TODAY
        
        year, month = ref.year, ref.month
        ld = monthrange(year, month)[1]
        last_day = datetime.datetime(year, month, ld)
        start_day = max(1, ld - (n - 1))
        start = datetime.datetime(year, month, start_day)
        return start, last_day
    
    def _parse_half_month(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse 'nửa đầu/cuối tháng' expressions."""
        # With explicit month and year (MM/YYYY format)
        m = re.search(r'nửa\s+(đầu|cuối|sau)\s+tháng\s+(1[0-2]|[1-9])\s*[\/\-]\s*(\d{2,4})', text)
        if m:
            which = m.group(1)
            month = int(m.group(2))
            y_raw = m.group(3)
            year = int(y_raw) if len(y_raw) == 4 else int(y_raw) + 2000
            ld = monthrange(year, month)[1]
            if which == 'đầu':
                return datetime.datetime(year, month, 1), datetime.datetime(year, month, min(15, ld))
            else:
                return datetime.datetime(year, month, 16), datetime.datetime(year, month, ld)
        
        # With explicit month number
        m = re.search(r'nửa\s+(đầu|cuối|sau)\s+tháng\s+(1[0-2]|[1-9])(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?', text)
        if m:
            which = m.group(1)
            month = int(m.group(2))
            year = self._resolve_year_modifier(m.group(3))
            ld = monthrange(year, month)[1]
            if which == 'đầu':
                return datetime.datetime(year, month, 1), datetime.datetime(year, month, min(15, ld))
            else:
                return datetime.datetime(year, month, 16), datetime.datetime(year, month, ld)
        
        # Without explicit month
        m = re.search(r'nửa\s+(đầu|cuối|sau)\s+tháng(?:\s+(này|nay|ngoái|trước|sau))?', text)
        if m:
            which = m.group(1)
            mod = m.group(2)
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - relativedelta(months=1)
            elif mod == 'sau':
                ref = self.TODAY + relativedelta(months=1)
            else:
                ref = self.TODAY
            year, month = ref.year, ref.month
            ld = monthrange(year, month)[1]
            if which == 'đầu':
                return datetime.datetime(year, month, 1), datetime.datetime(year, month, min(15, ld))
            else:
                return datetime.datetime(year, month, 16), datetime.datetime(year, month, ld)
        
        return None
    
    def _parse_middle_of_month(self, match) -> Tuple[datetime.datetime, datetime.datetime]:
        """Parse 'giữa tháng' expressions (days 11-20)."""
        m_group = match.group(1)
        y_group = match.group(2)
        mod = match.group(3)
        
        year = self._resolve_year_modifier(y_group)
        
        if m_group and m_group.isdigit():
            month = int(m_group)
        else:
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - relativedelta(months=1)
            elif mod == 'sau':
                ref = self.TODAY + relativedelta(months=1)
            else:
                ref = self.TODAY
            year, month = ref.year, ref.month
        
        ld = monthrange(year, month)[1]
        start = datetime.datetime(year, month, 11)
        end = datetime.datetime(year, month, min(20, ld))
        return start, end
    
    def _parse_end_of_month(self, match) -> Tuple[datetime.datetime, datetime.datetime]:
        """Parse 'cuối tháng' expressions (last 11 days)."""
        m_group = match.group(1)
        y_group = match.group(2)
        mod = match.group(3)
        
        year = self._resolve_year_modifier(y_group)
        
        if m_group and m_group.isdigit():
            month = int(m_group)
        else:
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - relativedelta(months=1)
            elif mod == 'sau':
                ref = self.TODAY + relativedelta(months=1)
            else:
                ref = self.TODAY
            year, month = ref.year, ref.month
        
        ld = monthrange(year, month)[1]
        start = datetime.datetime(year, month, 21)
        end = datetime.datetime(year, month, ld)
        return start, end
    
    def _parse_start_of_month(self, match, text: str) -> Tuple[datetime.datetime, datetime.datetime]:
        """Parse 'đầu tháng' expressions (first 5 days)."""
        m_group = match.group(1)
        y_group = match.group(2)
        
        year = self._resolve_year_modifier(y_group)
        
        if m_group and m_group.isdigit():
            m = int(m_group)
        else:
            if re.search(r'\b(ngoái|trước)\b', text):
                ref = self.TODAY - relativedelta(months=1)
                year, m = ref.year, ref.month
            elif re.search(r'\b(sau)\b', text):
                ref = self.TODAY + relativedelta(months=1)
                year, m = ref.year, ref.month
            else:
                m = self.TODAY.month
        
        ld = monthrange(year, m)[1]
        start = datetime.datetime(year, m, 1)
        end_day = min(5, ld)
        end = datetime.datetime(year, m, end_day)
        return start, end
    
    def _parse_quarter(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse quarter-related expressions."""
        # Specific quarter parts (đầu/giữa/cuối quý N)
        match = re.search(r'(đầu|giữa|cuối)\s+quý\s+(\d+)(?:\s+(?:năm\s+)?(\d{4}|nay|này|ngoái|trước|sau|kia))?', text)
        if match:
            part = match.group(1)
            q = int(match.group(2))
            year = self._resolve_year_modifier(match.group(3))
            
            if 1 <= q <= 4:
                sm = 3 * q - 2
                em = 3 * q
                ld = monthrange(year, em)[1]
                quarter_start = datetime.datetime(year, sm, 1)
                quarter_end = datetime.datetime(year, em, ld)
                
                if part == 'đầu':
                    mid_month_ld = monthrange(year, sm)[1]
                    return quarter_start, datetime.datetime(year, sm, mid_month_ld)
                elif part == 'giữa':
                    mid_month = sm + 1
                    mid_month_ld = monthrange(year, mid_month)[1]
                    return datetime.datetime(year, mid_month, 1), datetime.datetime(year, mid_month, mid_month_ld)
                else:  # cuối
                    return datetime.datetime(year, em, 1), quarter_end
        
        # Start of quarter (đầu quý)
        m_head_quarter = re.search(r"đầu\s+quý(?:\s+(này|nay|trước|ngoái|sau))?(?:\s+(?:trong\s+)?(\d+)\s*ngày)?", text)
        if m_head_quarter:
            mod = m_head_quarter.group(1)
            days = m_head_quarter.group(2)
            year = self.CURRENT_YEAR
            q = (self.TODAY.month - 1) // 3 + 1
            
            if mod in ['trước', 'ngoái']:
                q -= 1
                if q < 1:
                    q += 4
                    year -= 1
            elif mod == 'sau':
                q += 1
                if q > 4:
                    q -= 4
                    year += 1
            
            sm = 3 * q - 2
            em = 3 * q
            quarter_start = datetime.datetime(year, sm, 1)
            quarter_end = datetime.datetime(year, em, monthrange(year, em)[1])
            
            if days:
                n = int(days)
                end = quarter_start + datetime.timedelta(days=(n - 1))
                if end > quarter_end:
                    end = quarter_end
                return quarter_start, end
            
            end = quarter_start + datetime.timedelta(days=9)
            if end > quarter_end:
                end = quarter_end
            return quarter_start, end
        
        # Specific quarter number (quý N)
        match = re.search(r'quý\s+(\d+)(?:\s+(?:năm\s+)?(\d{4}|nay|ngoái|trước|sau|kia))?', text)
        if match:
            q = int(match.group(1))
            year = self._resolve_year_modifier(match.group(2))
            
            if 1 <= q <= 4:
                sm = 3 * q - 2
                em = 3 * q
                ld = monthrange(year, em)[1]
                return datetime.datetime(year, sm, 1), datetime.datetime(year, em, ld)
        
        # General quarter (quý này/trước/sau)
        match = re.search(r'quý(?:\s+(này|nay|trước|ngoái|sau))?', text)
        if match:
            mod = match.group(1)
            year = self.CURRENT_YEAR
            q = (self.TODAY.month - 1) // 3 + 1
            
            if mod in ['trước', 'ngoái']:
                q -= 1
                if q < 1:
                    q += 4
                    year -= 1
            elif mod == 'sau':
                q += 1
                if q > 4:
                    q -= 4
                    year += 1
            
            sm = 3 * q - 2
            em = 3 * q
            ld = monthrange(year, em)[1]
            start = datetime.datetime(year, sm, 1)
            
            if mod in ['này', 'nay']:
                end = self.TODAY
                quarter_end = datetime.datetime(year, em, ld)
                if end > quarter_end:
                    end = quarter_end
                return start, end
            else:
                return start, datetime.datetime(year, em, ld)
        
        return None
    
    def _parse_specific_date(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse specific date expressions like 'ngày 30 tháng 1 năm ngoái'."""
        match = re.search(r'ngày\s+(\d{1,2})\s+tháng\s+(1[0-2]|[1-9])\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia)', text)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = self._resolve_year_modifier(match.group(3))
            
            # validate day
            ld = monthrange(year, month)[1]
            if 1 <= day <= ld:
                d = datetime.datetime(year, month, day)
                return d, d
        
        return None
    
    def _parse_month(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse month-related expressions."""
        # Month in format 'tháng 11/2024' or 'tháng 11-2024'
        match = re.search(r'tháng\s+(1[0-2]|[1-9])\s*[\/\-]\s*(\d{2,4})', text)
        if match:
            m = int(match.group(1))
            y_raw = match.group(2)
            y = int(y_raw)
            if len(y_raw) == 2:
                y += 2000
            ld = monthrange(y, m)[1]
            return datetime.datetime(y, m, 1), datetime.datetime(y, m, ld)
        
        # Month X Y years ago
        match = re.search(r'(?:\b(trong|vào)\s+)?tháng\s+(1[0-2]|[1-9])\s+(\d+)\s+năm\s+trước', text)
        if match:
            m = int(match.group(2))
            years_ago = int(match.group(3))
            year = self.CURRENT_YEAR - years_ago
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # General month expressions
        match = re.search(r'(?:\b(trong|vào)\s+)?tháng(?!\s+trong)\s+(1[0-2]|[1-9])(?:\s+năm\s+(\d{4}|nay|ngoái|trước|sau|kia))?', text)
        if match:
            m = int(match.group(2))
            year = self._resolve_year_modifier(match.group(3))
            if 1 <= m <= 12:
                ld = monthrange(year, m)[1]
                return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # 'tháng trong năm X' -> whole year
        match = re.search(r'tháng\s+trong\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia)', text)
        if match:
            year = self._resolve_year_modifier(match.group(1))
            return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
        
        # 'trong tháng' / 'trong tháng này/trước/sau'
        match = re.search(r'(?:\b(trong|vào)\s+)?tháng(?!\s*(?:\d|trong))(?:\s+(này|nay|ngoái|trước|sau))?', text)
        if match:
            mod = match.group(2)
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - relativedelta(months=1)
            elif mod == 'sau':
                ref = self.TODAY + relativedelta(months=1)
            else:
                ref = self.TODAY
            year, m = ref.year, ref.month
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        return None
    
    def _parse_year(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse year-related expressions."""
        # Middle of year (giữa năm)
        match = re.search(r'giữa\s+năm(?:\s+năm)?(?:\s+(\d{4}|nay|này|ngoái|trước|sau|kia))?', text)
        if match:
            year = self._resolve_year_modifier(match.group(1))
            m = 6
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # 'trong ngày' -> today
        match = re.search(r'\btrong\s+ngày\b', text)
        if match:
            return self.TODAY, self.TODAY
        
        # 'trong năm' (current year to today)
        match = re.search(r'\btrong\s+năm(?!\s+\d)(?:\s+(nay|này))?\b', text)
        if match:
            return datetime.datetime(self.CURRENT_YEAR, 1, 1), self.TODAY
        
        # Explicit year
        match = re.search(r'(?:\b(trong|vào)\s+)?năm\s+(\d{4}|nay|này|ngoái|trước|sau|kia)', text)
        if match:
            year = self._resolve_year_modifier(match.group(2))
            return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
        
        return None
    
    def _parse_week(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse week-related expressions."""
        # Weekend (cuối tuần)
        match = re.search(r'cuối\s+tuần(?:\s+(này|nay|trước|ngoái|sau))?', text)
        if match:
            mod = match.group(1)
            ref = self.TODAY
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - datetime.timedelta(weeks=1)
            elif mod == 'sau':
                ref = self.TODAY + datetime.timedelta(weeks=1)
            offset = (5 - ref.weekday()) % 7
            sat = ref + datetime.timedelta(days=offset)
            sun = sat + datetime.timedelta(days=1)
            start = datetime.datetime(sat.year, sat.month, sat.day)
            end = datetime.datetime(sun.year, sun.month, sun.day)
            return start, end
        
        # Start of week (đầu tuần)
        match = re.search(r'đầu\s+tuần(?:\s+(này|nay|trước|ngoái|sau))?', text)
        if match:
            mod = match.group(1)
            ref = self.TODAY
            if mod in ['trước', 'ngoái']:
                ref = self.TODAY - datetime.timedelta(weeks=1)
            elif mod == 'sau':
                ref = self.TODAY + datetime.timedelta(weeks=1)
            mon = ref - datetime.timedelta(days=ref.weekday())
            start = datetime.datetime(mon.year, mon.month, mon.day)
            return start, start
        
        # General week expression
        if 'tuần' in text:
            d = self._parse_date_basic(text)
            if d:
                start = d - datetime.timedelta(days=d.weekday())
                end = start + datetime.timedelta(days=6)
                return start, end
        
        return None
    
    # ==================== RANGE PARSERS ====================
    
    def _parse_range_explicit(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse explicit date ranges with separators like 'từ...đến', 'từ...tới'."""
        separators = ['đến', 'tới', '-', 'cho đến']
        pattern = f"({'|'.join(separators)})"
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        if len(parts) >= 3:
            start_str = parts[0].replace("từ", "").strip()
            end_str = parts[-1].strip()
            start_range = self._parse_leaf_range(start_str)
            end_range = self._parse_leaf_range(end_str)
            
            if not start_range:
                start_range = self._parse_relative_range(start_str)
            if not end_range:
                end_range = self._parse_relative_range(end_str)
            
            if start_range and end_range:
                s0 = start_range[0]
                e1 = end_range[1]
                
                # Align years if start > end and no explicit year in start
                def start_has_year(s):
                    return bool(re.search(r'(?:[\/\-]\s*\d{4}\b)|\b\d{4}\b', s))
                
                if s0 > e1 and not start_has_year(start_str):
                    try:
                        s0 = s0.replace(year=e1.year)
                    except ValueError:
                        s0 = s0.replace(year=e1.year, day=28)
                
                return s0, e1
            
            # Fallback: extract explicit dates
            date_rx = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            s_match = re.findall(date_rx, start_str)
            e_match = re.findall(date_rx, end_str)
            s_date = None
            e_date = None
            
            if s_match:
                s_date = self._parse_date_basic(s_match[-1])
            if e_match:
                e_date = self._parse_date_basic(e_match[0])
            
            if s_date and e_date:
                def date_str_has_year(s):
                    return bool(re.search(r'(?:[\/\-]\s*\d{4}\b)|\b\d{4}\b', s))
                
                if s_date > e_date and not date_str_has_year(start_str):
                    try:
                        s_date = s_date.replace(year=e_date.year)
                    except ValueError:
                        s_date = s_date.replace(year=e_date.year, day=28)
                
                return s_date, e_date
            
            # Further fallback: two dates anywhere in text
            all_dates = re.findall(date_rx, text)
            if len(all_dates) >= 2:
                sd = self._parse_date_basic(all_dates[0])
                ed = self._parse_date_basic(all_dates[1])
                if sd and ed:
                    def token_has_4digit_year(tok):
                        return bool(re.search(r'\d{4}', tok))
                    
                    if sd > ed and not token_has_4digit_year(all_dates[0]):
                        try:
                            sd = sd.replace(year=ed.year)
                        except ValueError:
                            sd = sd.replace(year=ed.year, day=28)
                    
                    return sd, ed
        
        return None
    
    def _parse_relative_range(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse relative time ranges like '3 ngày trước', '2 tuần qua'."""
        # Skip if contains weekday or positional modifiers
        if re.search(r"\b(?:thứ\s*(?:hai|ba|bốn|tư|năm|sáu|bảy|[2-7])|thứ|chủ\s+nhật)\b", text):
            return None
        if re.search(r"\b(đầu|cuối|giữa)\b", text):
            return None
        # Skip if contains specific date pattern
        if re.search(r'ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm', text):
            return None
        
        NUM_WORD_MAP = {
            'một': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'năm': 5,
            'sáu': 6, 'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10
        }
        UNIT_ALIASES = {
            'ngày': 'ngày', 'day': 'ngày', 'days': 'ngày',
            'hôm': 'ngày',
            'tuần': 'tuần', 'tuan': 'tuần', 'week': 'tuần', 'weeks': 'tuần',
            'tháng': 'tháng', 'thang': 'tháng', 'month': 'tháng', 'months': 'tháng',
            'năm': 'năm', 'nam': 'năm', 'year': 'năm', 'years': 'năm'
        }
        
        directions = r'(qua|vừa qua|gần đây|gần nhất|gần đây nhất|tới|tiếp theo|trước|ngoái|ago)'
        unit_pattern = r'(hôm|ngày|tuần|tháng|năm|day|week|month|year|days|weeks|months|years|tuan|thang|nam)'
        
        # Try numeric
        m = re.search(rf'(?<!thứ\s)(\d+)\s+{unit_pattern}\s+{directions}', text)
        if m:
            num = int(m.group(1))
            unit_raw = m.group(2)
            direction = m.group(3)
            unit = UNIT_ALIASES.get(unit_raw, unit_raw)
        else:
            # Try word numbers
            m2 = re.search(rf'(?<!thứ\s)\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s+{unit_pattern}\s+{directions}', text)
            if m2:
                num = NUM_WORD_MAP.get(m2.group(1), 1)
                unit_raw = m2.group(2)
                direction = m2.group(3)
                unit = UNIT_ALIASES.get(unit_raw, unit_raw)
            else:
                # Implicit 1
                m3 = re.search(rf'\b{unit_pattern}\s+{directions}\b', text)
                if not m3:
                    return None
                num = 1
                unit_raw = m3.group(1)
                direction = m3.group(2)
                unit = UNIT_ALIASES.get(unit_raw, unit_raw)
        
        delta = {
            'ngày': relativedelta(days=num),
            'tuần': relativedelta(weeks=num),
            'tháng': relativedelta(months=num),
            'năm': relativedelta(years=num)
        }[unit]
        
        past_tokens = ['qua', 'vừa qua', 'gần đây', 'gần nhất', 'gần đây nhất', 'trước', 'ngoái', 'ago']
        if direction in past_tokens:
            if unit == 'tuần' and num >= 1:
                start_ref = self.TODAY - relativedelta(weeks=num)
                start = datetime.datetime(start_ref.year, start_ref.month, start_ref.day)
                end = self.TODAY
                return start, end
            
            if unit == 'năm' and num >= 1:
                year = self.TODAY.year - num
                return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
            
            if unit == 'tháng' and num >= 1:
                start_ref = self.TODAY - relativedelta(months=num)
                start_year, start_month = start_ref.year, start_ref.month
                start = datetime.datetime(start_year, start_month, 1)
                end_ref = self.TODAY - relativedelta(months=1)
                end_year, end_month = end_ref.year, end_ref.month
                end_ld = monthrange(end_year, end_month)[1]
                end = datetime.datetime(end_year, end_month, end_ld)
                return start, end
            
            if unit == 'ngày':
                start = self.TODAY - datetime.timedelta(days=num)
                end = self.TODAY - datetime.timedelta(days=1)
                return start, end
            else:
                return self.TODAY - delta, self.TODAY
        else:
            return self.TODAY, self.TODAY + delta
    
    def _parse_from_open(self, text: str) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """Parse 'từ X' patterns (from X to today)."""
        if text.lower().startswith("từ "):
            # Handle 'từ X đến nay'
            m = re.search(r'^từ\s+(.+?)\s+(?:đến|tới)\s+(nay|hôm nay|này)$', text.strip(), flags=re.IGNORECASE)
            if m:
                start_phrase = m.group(1).strip()
                r = self._parse_leaf_range(start_phrase)
                if r:
                    return r[0], self.TODAY
            
            # Fallback: 'từ X' -> from X to today
            s = text[3:].strip()
            r = self._parse_leaf_range(s)
            if r:
                return r[0], self.TODAY
        
        return None


# Backward compatibility function
def convert_nlp_to_date_range(text: str, current_date: Optional[datetime.datetime] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert Vietnamese natural language time expression to date range.
    This function provides backward compatibility with the old API.
    
    Args:
        text: Vietnamese time expression
        current_date: Optional reference date (defaults to now)
        
    Returns:
        Tuple of (start_date, end_date) in 'YYYY-MM-DD' format
    """
    parser = VietnameseTimeParser(current_date)
    return parser.parse(text)


# Example usage and testing
if __name__ == "__main__":
    parser = VietnameseTimeParser()
    
    tests = [
        'từ giữa tháng đến cuối tháng',
        'từ giữa tháng tới cuối tháng',
        'ngày 30 tháng 1 năm ngoái',
        'ngày 30 tháng 1 năm kia',
        '3 ngày trước',
        'đầu quý 1',
        'giữa quý 1',
        'cuối quý 1',
        'giữa quý 1 đến cuối quý 1',
        'tháng này',
        'năm ngoái',
        'năm kia',
    ]
    
    print("Vietnamese Time Parser - Test Results:")
    print("=" * 60)
    for test in tests:
        start, end = parser.parse(test)
        print(f"{test:35s} => {start} to {end}")