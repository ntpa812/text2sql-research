import re
import datetime
from calendar import monthrange
import dateparser
from dateutil.relativedelta import relativedelta


class TimeParser:
    """Vietnamese time expression parser for NER inference"""
    
    def __init__(self):
        """Initialize the TimeParser with current date/time context"""
        self.CURRENT_YEAR = datetime.datetime.now().year
        self.TODAY = datetime.datetime.now()
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
    
    def format_date(self, d):
        """Format datetime to string YYYY-MM-DD"""
        return d.strftime('%Y-%m-%d')
    
    def parse_date_basic(self, text):
        """Parse basic date using dateparser"""
        return dateparser.parse(text, languages=['vi'], settings={
            'DATE_ORDER': 'DMY',
            'PREFER_DAY_OF_MONTH': 'first',
            'PREFER_DATES_FROM': 'current_period'
        })
    
    def normalize_vi_numbers(self, text):
        """Normalize Vietnamese number words to digits"""
        text = text.lower()
        for word, num in self.VI_NUMBER_MAP.items():
            pattern = rf'\b({word})\s+{self.TIME_UNITS}\b'
            text = re.sub(pattern, rf'{num} \2', text)
        return text
    
    def parse_leaf_range(self, text):
        """Parse single time expressions (not ranges)"""
        text = text.strip().lower()
        
        # hôm nay / nay
        if text in ['nay', 'hôm nay', 'hiện tại', 'bây giờ']:
            return self.TODAY, self.TODAY
        
        # weekdays
        wd_match = re.search(r"\b(?:(chủ\s*nhật)|thứ\s*(hai|ba|bốn|tư|năm|sáu|bảy|[2-7]))(?:\s+tuần(?:\s+(nay|này|trước|ngoái|sau))?)?\b", text)
        if wd_match:
            sunday = wd_match.group(1)
            word = wd_match.group(2)
            mod = wd_match.group(3)
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
        
        # đầu năm
        match = re.search(r'\bđầu\s+năm(?:\s+(\d{4}|nay|này|ngoái|trước|sau))?', text)
        if match:
            y = match.group(1)
            year = self.CURRENT_YEAR
            if y and y.isdigit():
                year = int(y)
            elif y in ['nay', 'này']:
                year = self.CURRENT_YEAR
            elif y in ['ngoái', 'trước']:
                year -= 1
            elif y == 'sau':
                year += 1
            start = datetime.datetime(year, 1, 1)
            end = datetime.datetime(year, 1, 10)
            return start, end
        
        # cuối năm
        match = re.search(r'cuối\s+năm(?:\s+(?:(\d{4})|(nay|này|ngoái|trước|sau)))?', text)
        if match:
            y_digit = match.group(1)
            mod = match.group(2)
            year = self.CURRENT_YEAR
            if y_digit:
                year = int(y_digit)
            elif mod in ['ngoái', 'trước']:
                year -= 1
            elif mod == 'sau':
                year += 1
            start = datetime.datetime(year, 12, 27)
            end = datetime.datetime(year, 12, 31)
            return start, end
        
        # nửa đầu/cuối tháng
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

        m = re.search(r'nửa\s+(đầu|cuối|sau)\s+tháng\s+(1[0-2]|[1-9])(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau))?', text)
        if m:
            which = m.group(1)
            month = int(m.group(2))
            y_group = m.group(3)
            year = self.CURRENT_YEAR
            if y_group in ['ngoái', 'trước']:
                year -= 1
            elif y_group == 'sau':
                year += 1
            elif y_group and y_group.isdigit():
                year = int(y_group)
            ld = monthrange(year, month)[1]
            if which == 'đầu':
                return datetime.datetime(year, month, 1), datetime.datetime(year, month, min(15, ld))
            else:
                return datetime.datetime(year, month, 16), datetime.datetime(year, month, ld)

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
        
        # đầu tháng
        match = re.search(r'(?<!nửa\s)đầu\s+tháng(?:\s+(1[0-2]|[1-9]))?(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau))?', text)
        if match:
            m_group = match.group(1)
            y_group = match.group(2)
            year = self.CURRENT_YEAR
            if y_group in ['ngoái', 'trước']:
                year -= 1
            elif y_group == 'sau':
                year += 1
            elif y_group and y_group.isdigit():
                year = int(y_group)
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
        
        # cuối tháng / cuối tháng X / cuối tháng X năm Y
        match = re.search(r'(?<!nửa\s)cuối\s+tháng(?:\s+(1[0-2]|[1-9]))?(?:\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau))?', text)
        if match:
            m_group = match.group(1)
            y_group = match.group(2)
            year = self.CURRENT_YEAR
            if y_group in ['ngoái', 'trước']:
                year -= 1
            elif y_group == 'sau':
                year += 1
            elif y_group and y_group.isdigit():
                year = int(y_group)
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
            start = datetime.datetime(year, m, 25)
            end = datetime.datetime(year, m, ld)
            return start, end
        
        # hôm kia
        if text in ["hôm kia", "ngày hôm kia", "ngày kia"]:
            d = self.TODAY - datetime.timedelta(days=2)
            return d, d
        
        # đầu quý
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

        # quý này/trước/sau
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

        # quý N
        match = re.search(r'quý\s+(\d+)(?:\s+(?:năm\s+)?(\d{4}|nay|ngoái|trước|sau))?', text)
        if match:
            q = int(match.group(1))
            year = self.CURRENT_YEAR
            y = match.group(2)
            if y in ['ngoái', 'trước']:
                year -= 1
            elif y == 'sau':
                year += 1
            elif y and y.isdigit():
                year = int(y)
            if 1 <= q <= 4:
                sm = 3 * q - 2
                em = 3 * q
                ld = monthrange(year, em)[1]
                return datetime.datetime(year, sm, 1), datetime.datetime(year, em, ld)
        
        # trong tháng
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
        
        # weekday specific
        if re.search(r"\b(?:thứ\s*(?:hai|ba|bốn|tư|năm|sáu|bảy|[2-7])|chủ\s+nhật)\b", text):
            d = self.parse_date_basic(text)
            if d:
                return d, d
        
        # giữa năm
        match = re.search(r'giữa\s+năm(?:\s+năm)?(?:\s+(\d{4}|nay|này|ngoái|trước|sau))?', text)
        if match:
            y = match.group(1)
            year = self.CURRENT_YEAR
            if y and y.isdigit():
                year = int(y)
            elif y in ['nay', 'này']:
                year = self.CURRENT_YEAR
            elif y in ['ngoái', 'trước']:
                year -= 1
            elif y == 'sau':
                year += 1
            m = 6
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # trong ngày
        match = re.search(r'\btrong\s+ngày\b', text)
        if match:
            return self.TODAY, self.TODAY
        
        # tháng M/YYYY
        match = re.search(r'tháng\s+(1[0-2]|[1-9])\s*[\/\-]\s*(\d{2,4})', text)
        if match:
            m = int(match.group(1))
            y_raw = match.group(2)
            y = int(y_raw)
            if len(y_raw) == 2:
                y += 2000
            year = y
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # tháng X Y năm trước
        match = re.search(r'(?:\b(trong|vào)\s+)?tháng\s+(1[0-2]|[1-9])\s+(\d+)\s+năm\s+trước', text)
        if match:
            m = int(match.group(2))
            years_ago = int(match.group(3))
            year = self.CURRENT_YEAR - years_ago
            ld = monthrange(year, m)[1]
            return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # tháng M
        match = re.search(r'(?:\b(trong|vào)\s+)?tháng(?!\s+trong)\s+(1[0-2]|[1-9])(?:\s+năm\s+(\d{4}|nay|ngoái|trước|sau))?', text)
        if match:
            m = int(match.group(2))
            year = self.CURRENT_YEAR
            y = match.group(3)
            if y in ['ngoái', 'trước']:
                year -= 1
            elif y == 'sau':
                year += 1
            elif y and y.isdigit():
                year = int(y)
            if 1 <= m <= 12:
                ld = monthrange(year, m)[1]
                return datetime.datetime(year, m, 1), datetime.datetime(year, m, ld)
        
        # tháng trong năm
        match = re.search(r'tháng\s+trong\s+năm\s+(\d{4}|nay|này|ngoái|trước|sau)', text)
        if match:
            y = match.group(1)
            year = self.CURRENT_YEAR
            if y in ['nay', 'này']:
                year = self.CURRENT_YEAR
            elif y in ['ngoái', 'trước']:
                year = self.CURRENT_YEAR - 1
            elif y == 'sau':
                year = self.CURRENT_YEAR + 1
            else:
                year = int(y)
            return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
        
        # trong năm
        match = re.search(r'\btrong\s+năm(?!\s+\d)(?:\s+(nay|này))?\b', text)
        if match:
            return datetime.datetime(self.CURRENT_YEAR, 1, 1), self.TODAY
        
        # năm YYYY
        match = re.search(r'(?:\b(trong|vào)\s+)?năm\s+(\d{4}|nay|này|ngoái|trước|sau)', text)
        if match:
            y = match.group(2)
            year = self.CURRENT_YEAR
            if y in ['nay', 'này']:
                year = self.CURRENT_YEAR
            elif y in ['ngoái', 'trước']:
                year = self.CURRENT_YEAR - 1
            elif y == 'sau':
                year = self.CURRENT_YEAR + 1
            else:
                year = int(y)
            return datetime.datetime(year, 1, 1), datetime.datetime(year, 12, 31)
        
        # cuối tuần
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
        
        # đầu tuần
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

        # tuần
        if 'tuần' in text:
            d = self.parse_date_basic(text)
            if d:
                start = d - datetime.timedelta(days=d.weekday())
                end = start + datetime.timedelta(days=6)
                return start, end
        
        # ngày đơn
        d = self.parse_date_basic(text)
        if d:
            return d, d
        return None
    
    def parse_range_explicit(self, text):
        """Parse explicit ranges with separators like 'đến', 'tới'"""
        separators = ['đến', 'tới', '-', 'cho đến']
        pattern = f"({'|'.join(separators)})"
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        if len(parts) >= 3:
            start_str = parts[0].replace("từ", "").strip()
            end_str = parts[-1].strip()
            start_range = self.parse_leaf_range(start_str)
            end_range = self.parse_leaf_range(end_str)
            
            if not start_range:
                start_range = self.parse_relative_range(start_str)
            if not end_range:
                end_range = self.parse_relative_range(end_str)
            
            if start_range and end_range:
                s0 = start_range[0]
                e1 = end_range[1]
                
                def start_has_year(s):
                    return bool(re.search(r'(?:[\/\-]\s*\d{4}\b)|\b\d{4}\b', s))
                
                if s0 > e1 and not start_has_year(start_str):
                    try:
                        s0 = s0.replace(year=e1.year)
                    except ValueError:
                        s0 = s0.replace(year=e1.year, day=28)
                return s0, e1
            
            # fallback
            date_rx = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
            s_match = re.findall(date_rx, start_str)
            e_match = re.findall(date_rx, end_str)
            s_date = None
            e_date = None
            if s_match:
                s_date = self.parse_date_basic(s_match[-1])
            if e_match:
                e_date = self.parse_date_basic(e_match[0])
            if s_date and e_date:
                def date_str_has_year(s):
                    return bool(re.search(r'(?:[\/\-]\s*\d{4}\b)|\b\d{4}\b', s))
                if s_date > e_date and not date_str_has_year(start_str):
                    try:
                        s_date = s_date.replace(year=e_date.year)
                    except ValueError:
                        s_date = s_date.replace(year=e_date.year, day=28)
                return s_date, e_date
            
            all_dates = re.findall(date_rx, text)
            if len(all_dates) >= 2:
                sd = self.parse_date_basic(all_dates[0])
                ed = self.parse_date_basic(all_dates[1])
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
    
    def parse_relative_range(self, text):
        """Parse relative time ranges like 'N tháng qua'"""
        if re.search(r"\b(?:thứ\s*(?:hai|ba|bốn|tư|năm|sáu|bảy|[2-7])|thứ|chủ\s+nhật)\b", text):
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
        
        m = re.search(rf'(?<!thứ\s)(\d+)\s+{unit_pattern}\s+{directions}', text)
        if m:
            num = int(m.group(1))
            unit_raw = m.group(2)
            direction = m.group(3)
            unit = UNIT_ALIASES.get(unit_raw, unit_raw)
        else:
            m2 = re.search(rf'(?<!thứ\s)\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s+{unit_pattern}\s+{directions}', text)
            if m2:
                num = NUM_WORD_MAP.get(m2.group(1), 1)
                unit_raw = m2.group(2)
                direction = m2.group(3)
                unit = UNIT_ALIASES.get(unit_raw, unit_raw)
            else:
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
    
    def parse_from_open(self, text):
        """Parse open-ended ranges like 'từ X'"""
        if text.lower().startswith("từ "):
            m = re.search(r'^từ\s+(.+?)\s+(?:đến|tới)\s+(nay|hôm nay|này)$', text.strip(), flags=re.IGNORECASE)
            if m:
                start_phrase = m.group(1).strip()
                r = self.parse_leaf_range(start_phrase)
                if r:
                    return r[0], self.TODAY
            s = text[3:].strip()
            r = self.parse_leaf_range(s)
            if r:
                return r[0], self.TODAY
        return None
    
    def parse(self, text):
        """
        Main parsing method - convert Vietnamese time expression to date range.
        
        Args:
            text (str): Vietnamese time expression
            
        Returns:
            tuple: (start_date_str, end_date_str) in format 'YYYY-MM-DD' or (None, None)
        """
        text = self.normalize_vi_numbers(text)
        text = text.strip()
        
        for parser in [
            self.parse_range_explicit,
            self.parse_relative_range,
            self.parse_from_open
        ]:
            r = parser(text)
            if r:
                return self.format_date(r[0]), self.format_date(r[1])
        
        r = self.parse_leaf_range(text)
        if r:
            return self.format_date(r[0]), self.format_date(r[1])
        
        return None, None
    
    def __call__(self, text):
        """Make the parser callable for easier inference usage"""
        return self.parse(text)


# Example usage for inference
if __name__ == "__main__":
    parser = TimeParser()
    
    test_cases = [
        'trong ngày',
        'hôm nay',
        'tuần trước',
        '3 tháng qua',
        'quý 2 năm 2024',
        'từ tháng 1 đến tháng 3',
        'trong năm 2024',
        'đầu năm',
        'cuối tháng',
        'cuối tháng 2',
        'cuối tháng 12 năm 2024',
        'đầu tháng'
    ]
    
    print("Time Parser Inference Examples:")
    print("=" * 60)
    for test in test_cases:
        start, end = parser(test)
        print(f"{test:25} => {start} to {end}")
