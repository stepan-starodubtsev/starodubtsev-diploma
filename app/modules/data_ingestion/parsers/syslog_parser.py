# app/modules/data_ingestion/parsers/syslog_parser.py
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Any

# Приклад типового формату Syslog від Mikrotik (може трохи відрізнятися):
# <PRI>MMM DD HH:MM:SS HOSTNAME TAG: MESSAGE
# Наприклад: <78>May 30 12:34:56 MikrotikRouter firewall,info: input: in:ether1 out:(none), src-mac 00:0c:29:11:22:33, proto TCP (SYN), 192.168.1.100:12345->192.168.88.1:80, len 52
# Або: <134>May 30 12:35:00 MyRouter system,info,account user admin logged in from 192.168.1.50 via ssh

# Спрощений регулярний вираз для розбору такого формату.
# Його потрібно буде адаптувати під конкретні логи, які генерує твій Mikrotik.
# Цей вираз намагається виділити пріоритет, дату, хост, тег/програму та саме повідомлення.
# Для дати формату "MMM DD HH:MM:SS" рік не вказується, тому ми будемо додавати поточний рік.
SYSLOG_RFC3164_REGEX = re.compile(
    r"^\<(?P<priority>\d+)\>"  # Пріоритет: <123>
    r"(?P<timestamp_str>"  # Початок групи для часу
    r"(?P<month>\w{3})\s+"  # Місяць: Jan, Feb, ...
    r"(?P<day>\s?\d{1,2})\s+"  # День: (пробіл)1, 2, ... 31
    r"(?P<time>\d{2}:\d{2}:\d{2})"  # Час: HH:MM:SS
    r")\s+"
    r"(?P<hostname>[\w\-\.]+)\s+"  # Хост: myrouter, some-host.example.com
    r"(?P<process_tag>(?P<process_name>[\w\-\/\.\_]+)(\[(?P<pid>\d+)\])?)?:\s*"  # Тег процесу: program[pid]: або program:
    r"(?P<message>.+)$"  # Повідомлення: все інше
)

# Альтернативний, більш гнучкий, якщо тег не завжди є або має інший формат:
SYSLOG_REGEX_GENERIC = re.compile(
    r"^\<(?P<priority>\d+)\>"
    r"(?P<timestamp_str>\w{3}\s+\s?\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"  # MMM DD HH:MM:SS
    r"(?P<hostname>[\w\-\.]+)\s+"
    r"(?P<message>.+)$"  # Все інше вважаємо повідомленням, тег будемо шукати всередині
)


def parse_syslog_message_rfc3164_like(line: str, current_year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Розбирає syslog повідомлення, схоже на формат RFC3164 (BSD syslog).
    Додає поточний рік до мітки часу, оскільки він відсутній у цьому форматі.
    """
    print("Line:" + str(line))
    match = SYSLOG_RFC3164_REGEX.match(line)
    if not match:
        # Спробуємо більш загальний регекс, якщо перший не спрацював
        match_generic = SYSLOG_REGEX_GENERIC.match(line)
        if not match_generic:
            # print(f"DEBUG: Line did not match any syslog regex: {line}")
            return None  # Повертаємо None, якщо рядок не відповідає формату

        data = match_generic.groupdict()
        # У цьому випадку тег/програма є частиною повідомлення, її можна спробувати витягти додатково
        # Наприклад, якщо повідомлення починається з "programname:" або "programname[pid]:"
        message_parts = data['message'].split(":", 1)
        if len(message_parts) > 1:
            potential_tag = message_parts[0]
            # Проста перевірка, чи це схоже на тег (без пробілів, можливо з [])
            if not re.search(r"\s", potential_tag) and len(potential_tag) < 50:  # Обмеження довжини тегу
                process_match = re.match(r"^(?P<process_name>[\w\-\/\.\_]+)(\[(?P<pid>\d+)\])?$", potential_tag)
                if process_match:
                    data['process_tag'] = potential_tag
                    data['process_name'] = process_match.group('process_name')
                    data['pid'] = process_match.group('pid')
                    data['message'] = message_parts[1].strip()
    else:
        data = match.groupdict()

    # Обробка пріоритету для отримання Facility та Severity
    try:
        priority = int(data['priority'])
        facility = priority // 8
        severity = priority % 8
        data['facility'] = facility
        data['severity'] = severity
    except (ValueError, TypeError):
        data['facility'] = None
        data['severity'] = None

    # Обробка мітки часу
    # Формат RFC3164 не містить рік, тому додаємо поточний
    if not current_year:
        current_year = datetime.now(timezone.utc).year

    timestamp_str_from_log = data.get('timestamp_str')
    if timestamp_str_from_log:
        try:
            # Парсимо дату, додаючи рік. Приклад: "May 30 12:34:56"
            # Важливо: datetime.strptime не дуже добре обробляє подвійні пробіли перед днем, якщо день < 10 (напр. "May  1")
            # Регекс вже мав би це обробити (через \s?\d{1,2}), але для надійності
            timestamp_str_cleaned = re.sub(r'\s+', ' ',
                                           timestamp_str_from_log.strip())  # Замінюємо множинні пробіли на один

            dt_obj = datetime.strptime(f"{current_year} {timestamp_str_cleaned}", "%Y %b %d %H:%M:%S")
            # Встановлюємо часову зону як UTC, якщо логи приходять без неї,
            # або локальну зону, якщо відомо, що логи в локальному часі пристрою.
            # Для простоти припустимо, що час у лозі - це локальний час системи, де запущено парсер,
            # або UTC, якщо пристрій налаштований на UTC.
            # Найкраще, якщо пристрій надсилає логи з часовою зоною або в UTC.
            # Якщо це локальний час пристрою, і він відрізняється від UTC, потрібна буде конвертація.
            # Наразі, припустимо, що ми хочемо зберегти час як "aware" datetime в UTC.
            # Якщо час з логу є локальним для машини, де запущено парсер:
            # dt_obj = dt_obj.astimezone(timezone.utc)
            # Якщо ми припускаємо, що час з логу вже в UTC (часто так налаштовують сервери):
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)  # Робимо "aware" datetime в UTC
            data['timestamp'] = dt_obj
        except ValueError as e:
            # print(f"DEBUG: Error parsing timestamp '{timestamp_str_from_log}': {e}")
            data['timestamp'] = datetime.now(timezone.utc)  # Запасний варіант
            data['timestamp_parse_error'] = str(e)
    else:
        data['timestamp'] = datetime.now(timezone.utc)  # Якщо мітки часу немає взагалі

    # Видаляємо непотрібні проміжні поля
    data.pop('timestamp_str', None)
    data.pop('month', None)
    data.pop('day', None)
    data.pop('time', None)

    return data


# Простий тест для парсера
if __name__ == '__main__':
    test_lines = [
        "<78>May 30 10:10:32 MikrotikRouter firewall,info: input: in:ether1 out:(none), src-mac 00:0c:29:11:22:33, proto TCP (SYN), 192.168.1.100:12345->192.168.88.1:80, len 52",
        "<134>May 30 12:35:00 MyRouter system,info,account user admin logged in from 192.168.1.50 via ssh",
        "<27>May  1 08:00:00 somehost kernel: Program started.",
        "<165>May 30 11:22:33 another-host app/my_process[12345]: This is a message with a PID",
        "<165>May 30 11:23:44 short-host app_no_pid: This is a message without PID but with a program name",
        "This is not a syslog message",
        "<30>May 30 14:01:59 192.168.88.1 drop input: in:ether1 out:(none), proto UDP, 192.168.1.101:5353->224.0.0.251:5353, len100"
        # Mikrotik firewall log
    ]

    print("--- Testing SYSLOG_RFC3164_REGEX based parser ---")
    for line in test_lines:
        parsed = parse_syslog_message_rfc3164_like(line)
        if parsed:
            print(f"RAW: {line}")
            print(f"PARSED: {parsed}\n")
        else:
            print(f"RAW: {line}")
            print("PARSED: FAILED TO PARSE\n")
