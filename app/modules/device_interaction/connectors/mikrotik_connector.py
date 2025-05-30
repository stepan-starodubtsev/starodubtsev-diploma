# app/modules/device_interaction/connectors/mikrotik_connector.py
import routeros_api
from routeros_api.exceptions import (
    RouterOsApiConnectionError,
    RouterOsApiCommunicationError,
    FatalRouterOsApiError as RouterOsTrapError,
    RouterOsApiError,
    RouterOsApiParsingError
)
from typing import List, Dict, Any, Optional
from .base_connector import BaseConnector, ConnectorConnectionError, \
    ConnectorCommandError  # Імпортуємо базовий клас та загальні винятки


class MikrotikConnector(BaseConnector):
    def __init__(self, host: str, username: str, password: str, port: Optional[int] = 8728):
        super().__init__(host, username, password, port)  # Викликаємо конструктор базового класу
        self.api = None  # Специфічно для Mikrotik API
        self.connection_pool = None  # Специфічно для Mikrotik API Pool

    def connect(self) -> None:
        if self.is_connected and self.connection_pool:
            self.disconnect()
        try:
            self.connection_pool = routeros_api.RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=True
            )
            self.api = self.connection_pool.get_api()

            self.api.get_resource('/system/identity').get()

            self.is_connected = True
            print(f"Successfully connected to Mikrotik {self.host} (via MikrotikConnector)")
        except RouterOsApiConnectionError as e:
            self.is_connected = False
            self.api = None
            self.connection_pool = None
            raise ConnectorConnectionError(f"Mikrotik connection failed to {self.host}: {e}")
        except RouterOsTrapError as e:  # Додамо обробку TrapError тут, якщо перевірочна команда його спричинить
            self.is_connected = False  # Якщо команда перевірки не пройшла через trap
            self.api = None
            self.connection_pool = None
            raise ConnectorConnectionError(
                f"Mikrotik connection check command failed with trap on {self.host}: {e.message}")
        except Exception as e:  # Для інших непередбачених помилок під час з'єднання
            self.is_connected = False
            self.api = None
            self.connection_pool = None
            if isinstance(e, RouterOsApiError):
                raise ConnectorConnectionError(f"Mikrotik API error during connection to {self.host}: {e}")
            raise ConnectorConnectionError(f"Unexpected Mikrotik connection error to {self.host}: {e}")

    def disconnect(self) -> None:
        if self.connection_pool:
            try:
                self.connection_pool.disconnect()
                print(f"Disconnected from Mikrotik {self.host} (via MikrotikConnector)")
            except Exception as e:
                # Не кидаємо виняток при помилці відключення, просто логуємо
                print(f"Error during Mikrotik disconnection from {self.host}: {e}")
            finally:
                self.api = None
                self.connection_pool = None
                self.is_connected = False
        self.is_connected = False

    def _internal_execute_command(self, path: str, command_name: str = "get", **params: Any) -> List[Dict[str, Any]]:
        if not self.is_connected or not self.api:
            raise ConnectorConnectionError("MikrotikConnector: Not connected to device.")
        try:
            resource = self.api.get_resource(path)
            response = getattr(resource, command_name)(**params)
            return response if isinstance(response, list) else [response] if response is not None else []
        except RouterOsTrapError as e:
            raise ConnectorCommandError(
                f"Mikrotik Trap: '{e.message}' on cmd '{command_name} {path}' (Params: {params})")
        except (RouterOsApiCommunicationError, RouterOsApiParsingError, RouterOsApiError) as e:
            raise ConnectorCommandError(f"Mikrotik API/Communication Error on cmd '{command_name} {path}': {e}")
        except Exception as e:  # Інші непередбачені помилки
            raise ConnectorCommandError(f"Unexpected Mikrotik error on cmd '{command_name} {path}': {e}")

    # --- Реалізація абстрактних методів ---

    def get_system_identity(self) -> Optional[Dict[str, Any]]:
        result = self._internal_execute_command("/system/identity", command_name="get")
        return result[0] if result else None

    def get_system_resource_info(self) -> Optional[Dict[str, Any]]:
        result = self._internal_execute_command("/system/resource", command_name="get")
        return result[0] if result else None

    def configure_syslog(self, target_host: str, target_port: int, action_name_prefix: str, topics: str) -> bool:
        action_name = f"{action_name_prefix}Syslog"
        try:
            # 1. Налаштувати/оновити syslog action
            existing_actions = self._internal_execute_command("/system/logging/action", command_name="get",
                                                              **{"?name": action_name})

            # Перетворюємо target_port на рядок
            action_params = {
                "name": action_name,
                "target": "remote",
                "remote": target_host,  # target_host вже є рядком
                "remote-port": str(target_port)  # <--- ОСЬ ТУТ ВИПРАВЛЕННЯ
            }

            if existing_actions:
                action_id = existing_actions[0].get("id")
                # Переконуємося, що action_id не None перед використанням
                if action_id:
                    self._internal_execute_command("/system/logging/action", command_name="set",
                                                   **{".id": action_id, **action_params})
                else:
                    # Якщо action_id не знайдено, можливо, потрібно видалити стару дію (якщо логіка це передбачає) і додати нову
                    # Або просто додати, ризикуючи дублікатом, якщо get не повернув id, але дія є
                    print(
                        f"Warning: Could not find .id for existing syslog action '{action_name}'. Attempting to add new one.")
                    self._internal_execute_command("/system/logging/action", command_name="add", **action_params)
            else:
                self._internal_execute_command("/system/logging/action", command_name="add", **action_params)

            # 2. Налаштувати/оновити правило логування syslog
            rule_prefix = f"{action_name_prefix}_rule"  # Використовуємо action_name_prefix для правила також
            existing_rules = self._internal_execute_command("/system/logging", command_name="get",
                                                            **{"?action": action_name, "?prefix": rule_prefix})
            rule_params = {"topics": topics, "action": action_name, "prefix": rule_prefix}
            if existing_rules:
                rule_id = existing_rules[0].get("id")
                if rule_id:
                    self._internal_execute_command("/system/logging", command_name="set",
                                                   **{".id": rule_id, **rule_params})
                else:
                    print(
                        f"Warning: Could not find .id for existing syslog rule with prefix '{rule_prefix}'. Attempting to add new one.")
                    self._internal_execute_command("/system/logging", command_name="add", **rule_params)
            else:
                self._internal_execute_command("/system/logging", command_name="add", **rule_params)
            return True
        except ConnectorCommandError as e:
            print(f"Mikrotik syslog configuration failed: {e}")
            return False

    def configure_netflow(self, target_host: str, target_port: int, interfaces: str, version: int,
                          active_timeout: str = "1m", inactive_timeout: str = "15s") -> bool:
        try:
            # 1. Налаштувати/оновити ціль для Traffic Flow
            target_address = f"{target_host}:{target_port}"
            existing_targets = self._internal_execute_command("/ip/traffic-flow/target", command_name="get",
                                                              **{"?address": target_address, "?version": str(version)})
            target_params = {"address": target_address, "version": str(version)}
            if existing_targets:
                target_id = existing_targets[0].get(".id")
                self._internal_execute_command("/ip/traffic-flow/target", command_name="set",
                                               **{".id": target_id, **target_params})
            else:
                self._internal_execute_command("/ip/traffic-flow/target", command_name="add", **target_params)

            # 2. Увімкнути Traffic Flow
            self._internal_execute_command(
                "/ip/traffic-flow",
                command_name="set",
                enabled="yes",
                interfaces=interfaces,
                active_flow_timeout=active_timeout,
                inactive_flow_timeout=inactive_timeout
            )
            return True
        except ConnectorCommandError as e:
            print(f"Mikrotik netflow configuration failed: {e}")
            return False

    def get_firewall_rules(self, chain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Отримує список правил файрволу /ip/firewall/filter."""
        params = {}
        if chain:
            # RouterOS API зазвичай використовує "?" для фільтрації полів
            params["?chain"] = chain

            # Команда 'getall' в деяких старих бібліотеках, або 'get' без параметрів для всіх.
        # 'print' команда в RouterOS CLI. Для API це зазвичай 'get'.
        return self._internal_execute_command("/ip/firewall/filter", command_name="get", **params)

    def _add_ip_to_list_internal(self, list_name: str, ip_address: str, comment: Optional[str] = None) -> bool:
        """Внутрішній метод для додавання IP до списку."""
        try:
            params = {"list": list_name, "address": ip_address}
            if comment: params["comment"] = comment
            self._internal_execute_command("/ip/firewall/address-list", command_name="add", **params)
            return True
        except ConnectorCommandError as e:
            if "failure: already have such entry" in str(e).lower() or "duplicate entry" in str(e).lower():
                print(f"IP {ip_address} already in list '{list_name}' on {self.host}.")
                return True
            print(f"Mikrotik _add_ip_to_list_internal failed: {e}") # Змінено для ясності
            return False

    def unblock_ip(self, list_name: str, ip_address: str) -> bool:
        """
        Видаляє IP-адресу із вказаного списку адрес.
        Перевіряє, чи IP дійсно видалено.
        """
        try:
            # 1. Знайти записи для видалення
            entries_to_remove = self._internal_execute_command(
                "/ip/firewall/address-list",
                command_name="get",
                **{"?list": list_name, "?address": ip_address}
            )

            if not entries_to_remove:
                print(f"IP {ip_address} not found in list '{list_name}' on {self.host}. Considered unblocked.")
                # Перевіримо правило, як просив користувач
                self._check_associated_firewall_rule(list_name, "forward", "drop", "src-address-list")
                return True

            # 2. Спробувати видалити знайдені записи
            for entry in entries_to_remove:
                entry_id = entry.get("id")
                if entry_id:
                    print(
                        f"Attempting to remove entry ID {entry_id} (IP: {ip_address}, List: {list_name}) from {self.host}.")
                    self._internal_execute_command(
                        "/ip/firewall/address-list",
                        command_name="remove",
                        **{".id": entry_id}
                    )
                    print(f"Remove command sent for entry ID {entry_id}.")
                else:
                    print(
                        f"Warning: Could not find .id for entry {entry} to remove IP {ip_address} from list {list_name}.")

            # 3. Верифікація: перевірити, чи IP дійсно видалено
            remaining_entries = self._internal_execute_command(
                "/ip/firewall/address-list",
                command_name="get",
                **{"?list": list_name, "?address": ip_address}
            )

            if not remaining_entries:
                print(f"Successfully verified removal of IP {ip_address} from list '{list_name}'.")
                self._check_associated_firewall_rule(list_name, "forward", "drop", "src-address-list")
                return True
            else:
                print(
                    f"ERROR: IP {ip_address} still found in list '{list_name}' after attempting removal. IDs: {[e.get('.id') for e in remaining_entries]}")
                self._check_associated_firewall_rule(list_name, "forward", "drop",
                                                     "src-address-list")  # Все одно перевіримо правило
                return False

        except ConnectorCommandError as e:
            # Якщо помилка "no such item" під час початкового 'get', це означає, що IP не було в списку
            if "no such item" in str(e).lower() and "get" in str(e).lower() and "/ip/firewall/address-list" in str(
                    e).lower():
                print(
                    f"IP {ip_address} was not found in list '{list_name}' (during initial get). Considered unblocked.")
                self._check_associated_firewall_rule(list_name, "forward", "drop", "src-address-list")
                return True
            print(f"Mikrotik unblock_ip command failed for IP {ip_address} in list {list_name}: {e}")
            return False
        except Exception as e_gen:  # Інші непередбачені помилки
            print(f"Unexpected error during Mikrotik unblock_ip for IP {ip_address} in list {list_name}: {e_gen}")
            return False

    def _check_associated_firewall_rule(self, list_name: str, chain: str, action: str, direction_list_field: str):
        """Допоміжний метод для перевірки та логування наявності правила файрволу."""
        try:
            firewall_rule = self._find_firewall_rule_for_address_list(list_name, chain, action, direction_list_field)
            if firewall_rule:
                print(
                    f"Associated firewall rule for list '{list_name}' (chain: {chain}, action: {action}, field: {direction_list_field}) still exists (ID: {firewall_rule.get('.id')}).")
            else:
                print(
                    f"Warning: No associated firewall rule found for list '{list_name}' with specified parameters (chain: {chain}, action: {action}, field: {direction_list_field}).")
        except ConnectorCommandError as e:
            print(f"Could not check for associated firewall rule for list '{list_name}': {e}")

    # Метод _find_firewall_rule_for_address_list та _create_firewall_rule_for_address_list
    # залишаються з попереднього прикладу. Переконайтеся, що вони є у вашому класі.
    def _find_firewall_rule_for_address_list(self, list_name: str, chain: str, action: str,
                                             direction_list_field: str) -> Optional[Dict[str, Any]]:
        rules = self.get_firewall_rules(chain=chain)
        for rule in rules:
            if rule.get("action") == action and rule.get(direction_list_field) == list_name:
                return rule
        return None

    def _create_firewall_rule_for_address_list(self, list_name: str, chain: str, action: str, direction_list_field: str,
                                               comment: str, place_at_top: bool = True) -> bool:
        try:
            # 1. Параметри для додавання правила (без 'numbers')
            add_params = {
                "chain": chain,
                "action": action,
                direction_list_field: list_name,
                "comment": comment
            }

            # Додаємо правило. Воно буде додано в кінець ланцюжка.
            # Команда add повертає список словників, де перший елемент - інформація про додане правило, включаючи .id
            added_rule_info_list = self._internal_execute_command("/ip/firewall/filter", command_name="add",
                                                                  **add_params)

            if not added_rule_info_list or not added_rule_info_list[0].get('.id'):
                print(f"Failed to add firewall rule or retrieve its .id for list '{list_name}' on {self.host}.")
                return False

            new_rule_id = added_rule_info_list[0]['.id']
            print(
                f"Firewall rule for list '{list_name}' added with ID {new_rule_id} in chain '{chain}' on {self.host}.")

            # 2. Якщо потрібно розмістити нагорі, переміщуємо його
            if place_at_top:
                print(f"Attempting to move rule {new_rule_id} to the top (position 0)...")
                # Команда move: 'numbers' - це ID або список ID правил, які потрібно перемістити.
                # 'destination' - це ID правила, ПЕРЕД яким потрібно вставити, або числовий індекс (0 для самого верху).
                # Якщо вказати просто '0', воно має перемістити на першу позицію.
                self._internal_execute_command(
                    "/ip/firewall/filter",
                    command_name="move",
                    numbers=new_rule_id,  # Яке правило переміщуємо
                    destination="0"  # Куди переміщуємо (на позицію 0)
                )
                print(f"Firewall rule {new_rule_id} moved to the top of chain '{chain}'.")

            return True
        except ConnectorCommandError as e:
            # Перевіряємо, чи помилка не пов'язана з тим, що ідентичне правило вже існує
            # (це складніше визначити без точного тексту помилки від RouterOS для "duplicate")
            # Зазвичай RouterOS дозволяє дублікати правил, якщо їх не ідентифікувати унікально.
            # Якщо 'add' не вдалося, то new_rule_id може бути не визначено.
            print(f"Failed to create or move firewall rule for list '{list_name}': {e}")
            return False

    # Метод block_ip викликає _create_firewall_rule_for_address_list
    # Параметр place_rule_at_top тепер буде використаний для визначення, чи переміщувати правило
    def block_ip(self, list_name: str, ip_address: str, comment: Optional[str] = None,
                 firewall_chain: str = "forward", firewall_action: str = "drop",
                 rule_comment_prefix: str = "SIEM_auto_block_for_",
                 place_rule_at_top: bool = True) -> bool:  # place_rule_at_top використовується
        try:
            add_comment = comment or f"Blocked by SIEM: {ip_address}"
            if not self._add_ip_to_list_internal(list_name, ip_address,
                                                 add_comment):  # _add_ip_to_list_internal з попередніх прикладів
                return False

            direction_list_field = "src-address-list"
            rule_comment = f"{rule_comment_prefix}{list_name}"

            # Перевіряємо, чи правило вже існує, щоб уникнути дублювання логіки створення,
            # хоча _create_firewall_rule_for_address_list має певну ідемпотентність (через find потім set/add)
            # але тут ми також перевіряємо, щоб не викликати створення без потреби.
            existing_rule = self._find_firewall_rule_for_address_list(list_name, firewall_chain, firewall_action,
                                                                      direction_list_field)

            if not existing_rule:
                print(f"Firewall rule for list '{list_name}' not found. Creating...")
                if not self._create_firewall_rule_for_address_list(list_name, firewall_chain, firewall_action,
                                                                   direction_list_field, rule_comment,
                                                                   place_rule_at_top):
                    # Не змінюємо повідомлення тут, бо воно вже детальне в _create_firewall_rule_for_address_list
                    return False
            else:
                print(
                    f"Firewall rule for list '{list_name}' already exists (ID: {existing_rule.get('.id')}). Placement check/update for existing rule not implemented here.")
                # Якщо правило існує, але ми хочемо переконатися, що воно нагорі,
                # потрібна додаткова логіка для 'move', якщо його поточна позиція не 0.
                # Для MVP, ми просто перевіряємо наявність.

            return True
        except ConnectorCommandError as e:
            print(f"Error during block_ip for {ip_address} in list {list_name}: {e}")
            return False