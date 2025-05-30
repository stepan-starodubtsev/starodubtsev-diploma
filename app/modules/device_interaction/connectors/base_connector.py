# app/modules/device_interaction/connectors/base_connector.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


# --- Загальні винятки для всіх конекторів ---
class ConnectorError(Exception):
    print(Exception)
    pass


class ConnectorConnectionError(ConnectorError):
    print(ConnectorError)
    pass


class ConnectorCommandError(ConnectorError):
    print(ConnectorError)
    pass


class BaseConnector(ABC):
    def __init__(self, host: str, username: str, password: str, port: Optional[int] = None):
        self.host = host
        self.username = username
        self.password = password  # Розшифрований пароль
        self.port = port
        self.is_connected = False

    @abstractmethod
    def connect(self) -> None:
        """Встановлює з'єднання з пристроєм."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Закриває з'єднання з пристроєм."""
        pass

    @abstractmethod
    def get_system_identity(self) -> Optional[Dict[str, Any]]:
        """
        Отримує ідентифікаційну інформацію про систему (наприклад, ім'я, модель).
        Повертає словник з даними або None у разі невдачі.
        """
        pass

    @abstractmethod
    def get_system_resource_info(self) -> Optional[Dict[str, Any]]:
        """
        Отримує інформацію про системні ресурси (наприклад, версія ОС, аптайм, CPU, пам'ять).
        Повертає словник з даними або None у разі невдачі.
        """
        pass

    @abstractmethod
    def configure_syslog(self, target_host: str, target_port: int, action_name_prefix: str, topics: str) -> bool:
        """
        Налаштовує відправку syslog на вказаний хост та порт.
        action_name_prefix - використовується для створення унікального імені дії/правила.
        Повертає True у разі успіху, False - у разі невдачі.
        """
        pass

    @abstractmethod
    def configure_netflow(self, target_host: str, target_port: int, interfaces: str, version: int,
                          active_timeout: str = "1m", inactive_timeout: str = "15s") -> bool:
        """
        Налаштовує відправку Netflow/IPFIX/TrafficFlow.
        Повертає True у разі успіху, False - у разі невдачі.
        """
        pass

    @abstractmethod
    def get_firewall_rules(self, chain: Optional[str] = None) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def block_ip(self, list_name: str, ip_address: str, comment: Optional[str] = None,
                 firewall_chain: str = "forward", firewall_action: str = "drop",
                 rule_comment_prefix: str = "SIEM_auto_block_rule_for_") -> bool:
        """
        Блокує IP-адресу: додає її до списку адрес та переконується,
        що існує відповідне правило у файрволі.
        Якщо правило не існує, намагається його створити.
        Повертає True у разі успіху, False - у разі невдачі.
        """
        pass

    @abstractmethod
    def unblock_ip(self, list_name: str, ip_address: str) -> bool:
        """
        Розблоковує IP-адресу: видаляє її зі списку адрес.
        Також перевіряє наявність списку та правила у файрволі (для інформації).
        Повертає True, якщо IP було видалено або його не було в списку.
        Повертає False, якщо сталася помилка під час видалення.
        """
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
