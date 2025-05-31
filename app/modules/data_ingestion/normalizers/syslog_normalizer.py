# app/modules/data_ingestion/normalizers/syslog_normalizer.py
from typing import Dict, Optional, Any
import re
from datetime import datetime, timezone
from pydantic import ValidationError  # Для обробки помилок валідації Pydantic

from .common_event_schema import CommonEventSchema

# Мапінг кодів severity Syslog на імена (можна розширити)
SYSLOG_SEVERITY_MAP = {
    0: "emergency", 1: "alert", 2: "critical", 3: "error",
    4: "warning", 5: "notice", 6: "informational", 7: "debug",
}


class SyslogNormalizer:
    def normalize(self, parsed_data: Dict[str, Any]) -> Optional[CommonEventSchema]:
        """
        Нормалізує розпарсені дані Syslog до CommonEventSchema.
        `parsed_data` - це словник, повернутий `parse_syslog_message_rfc3164_like`.
        """
        if not parsed_data:
            return None

        try:
            # Базові поля, які мають бути завжди з парсера або встановлені за замовчуванням
            event_timestamp = parsed_data.get('timestamp', datetime.now(timezone.utc))  # Парсер має повертати datetime

            # Переконуємося, що timestamp є aware datetime (має часову зону)
            if event_timestamp.tzinfo is None:
                # Якщо припускаємо, що час з логу вже в UTC, але naive
                event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
                # Якщо час з логу локальний для машини, що відправила, і потрібно конвертувати:
                # local_tz = datetime.now().astimezone().tzinfo # обережно, це tz машини, де запущено SIEM
                # event_timestamp = event_timestamp.replace(tzinfo=local_tz).astimezone(timezone.utc)

            common_event_data = {"timestamp": event_timestamp, "reporter_ip": parsed_data.get('reporter_ip'),
                                 "reporter_port": parsed_data.get('reporter_port'),
                                 "hostname": parsed_data.get('hostname'),
                                 "raw_log": parsed_data.get('raw_log', str(parsed_data)),
                                 "message": parsed_data.get('message'), "process_name": parsed_data.get('process_name'),
                                 "process_id": parsed_data.get('pid'), "syslog_facility": parsed_data.get('facility'),
                                 "syslog_severity_code": parsed_data.get('severity'),
                                 "syslog_severity_name": SYSLOG_SEVERITY_MAP.get(parsed_data.get('severity')),
                                 "additional_fields": {}, "device_vendor": "Mikrotik", "device_product": "RouterOS"}

            # ---- Спроба витягти специфічні дані для Mikrotik ----
            # Це приклад, його потрібно буде значно вдосконалити на основі реальних логів

            message_content = common_event_data.get("message", "")
            process_tag = parsed_data.get('process_tag', '')  # Наприклад "firewall,info" або "system,info,account"

            if "firewall" in process_tag.lower() or "drop input" in message_content.lower() or "allow input" in message_content.lower():  # Дуже приблизно
                common_event_data["event_category"] = "firewall"
                # Тут потрібен більш складний парсинг повідомлення Mikrotik Firewall
                # для витягнення src-ip, dst-ip, src-port, dst-port, proto, in-interface, out-interface, action (drop, accept, reject)
                # Наприклад: "input: in:ether1 out:(none), src-mac ..., proto TCP (SYN), 192.168.1.100:12345->192.168.88.1:80, len 52"
                # Це завдання для окремого парсера повідомлень Mikrotik Firewall.
                # Наразі, ми можемо спробувати витягти хоча б дію:
                if "drop" in message_content.lower():
                    common_event_data["event_action"] = "denied" common_event_data["event_outcome"] = "failure"
                elif "accept" in message_content.lower() or "allow" in message_content.lower():
                    common_event_data["event_action"] = "allowed" common_event_data["event_outcome"] = "success"
                elif "reject" in message_content.lower():
                    common_event_data["event_action"] = "denied" common_event_data["event_outcome"] = "failure"

                # Дуже спрощена спроба витягти IP (потребує значно кращого регексу)
                ip_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
                ips_found = re.findall(ip_pattern, message_content)
                if len(ips_found) >= 1: common_event_data["source_ip"] = ips_found[0]
                if len(ips_found) >= 2: common_event_data["destination_ip"] = ips_found[1]
                # Аналогічно для портів, протоколу тощо.

            elif "login" in process_tag.lower() or "logged in" in message_content.lower() or "login failure" in message_content.lower():
                common_event_data["event_category"] = "authentication"
                common_event_data["event_type"] = "user_login_attempt"
                if "logged in" in message_content.lower() and "failed" not in message_content.lower():
                    common_event_data["event_outcome"] = "success"
                else:
                    common_event_data["event_outcome"] = "failure"

            elif "system" in process_tag.lower():
                common_event_data["event_category"] = "system"

            # Зберігаємо нерозпізнані поля з parsed_data в additional_fields, якщо потрібно
            for key, value in parsed_data.items():
                if key not in common_event_data and key not in ["reporter_ip", "reporter_port", "raw_log", "priority",
                                                                "facility", "severity", "hostname", "message",
                                                                "process_name", "pid", "timestamp"]:
                    common_event_data["additional_fields"][f"parsed_{key}"] = value

            # Створюємо та валідуємо об'єкт CommonEventSchema
            normalized_event = CommonEventSchema(**common_event_data)
            return normalized_event

        except ValidationError as e:
            print(f"Pydantic ValidationError during syslog normalization: {e}")
            print(f"Problematic data: {common_event_data if 'common_event_data' in locals() else parsed_data}")
            return None
        except Exception as e:
            print(f"Unexpected error during syslog normalization: {e}")
            print(f"Problematic data: {parsed_data}")
            return None


# Простий тест для нормалізатора
if __name__ == '__main__':
    # Приклад розпарсених даних (імітація виходу з syslog_parser)
    sample_parsed_syslog = {
        'priority': 78,
        'facility': 9,  # mail system
        'severity': 6,  # informational
        'timestamp': datetime(2025, 5, 30, 10, 10, 32, tzinfo=timezone.utc),
        'hostname': 'MikrotikRouter',
        'process_tag': 'firewall,info',
        'process_name': None,  # Парсер може не витягти, якщо формат тегу складний
        'pid': None,
        'message': 'input: in:ether1 out:(none), src-mac 00:0c:29:11:22:33, proto TCP (SYN), 192.168.1.100:12345->192.168.88.1:80, len 52',
        'reporter_ip': '192.168.88.1',  # Додано сервісом
        'reporter_port': 514,  # Додано сервісом
        'raw_log': '<78>May 30 10:10:32 MikrotikRouter firewall,info: input: in:ether1 out:(none), src-mac 00:0c:29:11:22:33, proto TCP (SYN), 192.168.1.100:12345->192.168.88.1:80, len 52'
    }

    normalizer = SyslogNormalizer()
    normalized = normalizer.normalize(sample_parsed_syslog)

    if normalized:
        print("\n--- Normalized Event ---")
        print(normalized.model_dump_json(indent=2))  # Pydantic V2
        # print(normalized.json(indent=2)) # Pydantic V1
    else:
        print("Normalization failed.")

    sample_login_log = {
        'priority': 134, 'facility': 16, 'severity': 6,
        'timestamp': datetime(2025, 5, 30, 12, 35, 0, tzinfo=timezone.utc),
        'hostname': 'MyRouter', 'process_tag': 'system,info,account',
        'message': 'user admin logged in from 192.168.1.50 via ssh',
        'reporter_ip': '192.168.88.1', 'reporter_port': 514,
        'raw_log': '<134>May 30 12:35:00 MyRouter system,info,account user admin logged in from 192.168.1.50 via ssh'
    }
    normalized_login = normalizer.normalize(sample_login_log)
    if normalized_login:
        print("\n--- Normalized Login Event ---")
        print(normalized_login.model_dump_json(indent=2))