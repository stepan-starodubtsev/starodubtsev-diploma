# app/modules/data_ingestion/parsers/syslog_parser.py
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Any

# Мапінг кодів severity Syslog на імена (може бути винесений або синхронізований з normalizer)
SYSLOG_SEVERITY_MAP_PARSER = {  # Використовуємо іншу назву, щоб уникнути конфлікту, якщо імпортується звідкись ще
    0: "emergency", 1: "alert", 2: "critical", 3: "error",
    4: "warning", 5: "notice", 6: "informational", 7: "debug",
}

# Стандартний Syslog (RFC3164-подібний)
SYSLOG_RFC3164_REGEX = re.compile(
    r"^\<(?P<priority>\d+)\>"
    r"(?P<timestamp_str>"
    r"(?P<month>\w{3})\s+"
    r"(?P<day>\s?\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r")\s+"
    r"(?P<hostname>[\w\-\.]+)\s+"
    r"(?P<process_tag>(?P<process_name>[\w\-\/\.\_]+)(\[(?P<pid>\d+)\])?)?:\s*"
    r"(?P<message>.+)$"
)

# Більш загальний Syslog (якщо тег відсутній або має інший формат)
SYSLOG_REGEX_GENERIC = re.compile(
    r"^\<(?P<priority>\d+)\>"
    r"(?P<timestamp_str>\w{3}\s+\s?\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>[\w\-\.]+)\s+"
    r"(?P<message>.+)$"
)

# Регулярний вираз для спрощеного формату Mikrotik (теги<пробіл>повідомлення)
# Теги - це послідовність слів (букви, цифри, _, -), розділених комами, без пробілів всередині самих тегів.
MIKROTIK_SIMPLE_FORMAT_REGEX = re.compile(
    r"^(?P<mikrotik_topics>[a-zA-Z0-9\-_,]+)"  # Теги (наприклад, "firewall,info" або "system,info,account")
    r"\s+"  # Один або більше пробілів
    r"(?P<message>.+)$"  # Решта рядка - це повідомлення
)


def parse_syslog_message_rfc3164_like(line: str,
                                      reporter_ip: Optional[str] = None,
                                      current_year: Optional[int] = None
                                      ) -> Optional[Dict[str, Any]]:
    data: Optional[Dict[str, Any]] = None
    parsed_format = None

    # 1. Спроба розбору стандартного RFC3164-подібного формату

    match_rfc3164 = SYSLOG_RFC3164_REGEX.match(line)
    if match_rfc3164:
        data = match_rfc3164.groupdict()
        parsed_format = "rfc3164"
    else:
        # 2. Спроба розбору більш загального Syslog формату
        match_generic_syslog = SYSLOG_REGEX_GENERIC.match(line)
        if match_generic_syslog:
            data = match_generic_syslog.groupdict()
            parsed_format = "generic_syslog"
            # Спроба витягти тег/програму з повідомлення для загального формату
            message_parts = data['message'].split(":", 1)
            if len(message_parts) > 1:
                potential_tag = message_parts[0].strip()  # Додамо strip()
                # Перевірка, чи це схоже на тег (без пробілів, можливо з [])
                if not re.search(r"\s", potential_tag) and len(potential_tag) < 50:
                    process_match = re.match(r"^(?P<process_name>[\w\-\/\.\_]+)(\[(?P<pid>\d+)\])?$", potential_tag)
                    if process_match:
                        data['process_tag'] = potential_tag
                        data['process_name'] = process_match.group('process_name')
                        data['pid'] = process_match.group('pid')
                        data['message'] = message_parts[1].strip()
        else:
            # 3. Спроба розбору спрощеного формату Mikrotik
            # print(f"DEBUG: Trying MIKROTIK_SIMPLE_FORMAT_REGEX on line: '{line}'") # Для відладки
            match_mikrotik = MIKROTIK_SIMPLE_FORMAT_REGEX.match(line)
            if match_mikrotik:
                data = match_mikrotik.groupdict()
                parsed_format = "mikrotik_simple"

                data['priority'] = None
                data['facility'] = None
                data['severity'] = None
                data['timestamp'] = datetime.now(timezone.utc)  # Час отримання
                data['hostname'] = reporter_ip if reporter_ip else "unknown_mikrotik_host"

                # Використовуємо 'mikrotik_topics' як 'process_tag'
                data['process_tag'] = data.pop('mikrotik_topics',
                                               None)  # Видаляємо mikrotik_topics і зберігаємо в process_tag

                # Спроба витягти severity з topics
                if data['process_tag']:
                    topics_list = [t.strip().lower() for t in data['process_tag'].split(',')]
                    severity_map_reverse = {v: k for k, v in SYSLOG_SEVERITY_MAP_PARSER.items()}
                    for topic in topics_list:
                        if topic in severity_map_reverse:
                            data['severity'] = severity_map_reverse[topic]
                            # Можна встановити 'priority' за замовчуванням, якщо facility відомий (напр., 16 для local0)
                            # data['priority'] = (16 * 8) + data['severity'] if data['severity'] is not None else None
                            break
                # print(f"DEBUG: MIKROTIK_SIMPLE_FORMAT_REGEX Matched! Data: {data}") # Для відладки
                return data  # Для Mikrotik формату повертаємо одразу, бо обробка часу інша
            else:
                # print(f"DEBUG: No regex matched line: '{line}'") # Для відладки
                return None  # Жоден формат не підійшов

    # --- Цей блок виконується, якщо спрацював parsed_format == "rfc3164" або "generic_syslog" ---
    if not data:  # Якщо якимось чином сюди потрапили без даних
        return None

    # Обробка пріоритету для стандартних форматів
    priority_str = data.get('priority')
    if priority_str:
        try:
            priority_val = int(priority_str)
            data['facility'] = priority_val // 8
            data['severity'] = priority_val % 8
        except (ValueError, TypeError):
            data['facility'] = None;
            data['severity'] = None
    else:
        data['facility'] = None;
        data['severity'] = None

    # Обробка мітки часу для стандартних форматів
    timestamp_str_from_log = data.get('timestamp_str')
    if timestamp_str_from_log:
        effective_year = current_year if current_year else datetime.now(timezone.utc).year
        try:
            timestamp_str_cleaned = re.sub(r'\s+', ' ', timestamp_str_from_log.strip())
            dt_obj = datetime.strptime(f"{effective_year} {timestamp_str_cleaned}", "%Y %b %d %H:%M:%S")
            # Припускаємо, що час у лозі є локальним для джерела, і ми хочемо UTC.
            # Якщо немає інформації про часову зону джерела, це може бути неточно.
            # Поки що, для простоти, робимо його aware UTC.
            data['timestamp'] = dt_obj.replace(tzinfo=timezone.utc)
        except ValueError as e:
            data['timestamp'] = datetime.now(timezone.utc)  # Запасний варіант
            data['timestamp_parse_error'] = str(e)
    elif not data.get('timestamp'):  # Якщо timestamp ще не встановлено
        data['timestamp'] = datetime.now(timezone.utc)

    # Видаляємо проміжні поля від регексів для стандартних форматів
    for key in ['timestamp_str', 'month', 'day', 'time']:
        data.pop(key, None)

    return data


# ... (if __name__ == '__main__' блок для тестування, онови його для нових прикладів)
if __name__ == '__main__':
    test_lines_map = {
        "rfc3164_like": "<78>May 31 10:10:32 MikrotikRouter firewall,info: input: in:ether1 out:(none), src-mac ..., proto TCP ...",
        "mikrotik_system_identity": "system,info system identity changed by admin",
        "mikrotik_system_rule_changed": "system,info filter rule changed by admin",
        "mikrotik_firewall_tcp": "firewall,info OutgoingTraffic forward: in:bridge1 out:wlan1, src-mac 08:8f:c3:ea:87:dd, proto TCP (SYN), 192.168.88.253:57489->146.112.41.2:443, len 52",
        "mikrotik_firewall_udp": "firewall,info OutgoingTraffic forward: in:bridge1 out:wlan1, src-mac 08:8f:c3:ea:87:dd, proto UDP, 192.168.88.253:52660->216.58.215.110:443, len 1278",
        "unrecognized": "This is not a syslog message at all"
    }
    print("--- Testing Combined Syslog Parser ---")
    for name, line in test_lines_map.items():
        # Для тестів Mikrotik-формату передамо імітований IP відправника
        reporter_ip_test = "192.168.88.1" if "mikrotik" in name else "127.0.0.1"

        print(f"--- Test Case: {name} ---")
        print(f"RAW: {line}")
        parsed = parse_syslog_message_rfc3164_like(line, reporter_ip=reporter_ip_test)
        if parsed:
            print(f"PARSED: {parsed}\n")
        else:
            print("PARSED: FAILED TO PARSE\n")
