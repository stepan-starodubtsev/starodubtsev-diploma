# app/modules/data_ingestion/listeners/syslog_udp_listener.py
import socketserver
import threading  # Для запуску в окремому потоці


# Функція зворотного виклику, яка буде обробляти кожне отримане повідомлення
# Пізніше ми передамо сюди реальний обробник з service.py
def default_syslog_handler(raw_message: bytes, client_address: tuple):
    try:
        decoded_message = raw_message.decode('utf-8', errors='replace')
        print(f"SYSLOG from {client_address[0]}:{client_address[1]}: {decoded_message.strip()}")
        # Тут буде логіка передачі в парсер -> нормалізатор -> Elasticsearch
    except Exception as e:
        print(f"Error processing syslog message from {client_address}: {e}")


class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """
    Обробник для UDP Syslog повідомлень.
    """

    def __init__(self, request, client_address, server, message_handler_callback):
        self.message_handler_callback = message_handler_callback
        super().__init__(request, client_address, server)

    def handle(self):
        data = self.request[0]  # Отримуємо дані (байти)
        # socket = self.request[1] # Сокет (не використовується тут)
        # client_address = self.client_address # Адреса клієнта (вже є)
        self.message_handler_callback(data, self.client_address)


class SyslogUDPListener:
    def __init__(self, host: str = "0.0.0.0", port: int = 514,
                 message_handler_callback=default_syslog_handler):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.message_handler_callback = message_handler_callback

    def start(self):
        if self.server:
            print("Syslog UDP Listener is already running.")
            return

        print(f"Starting Syslog UDP Listener on {self.host}:{self.port}...")
        try:
            # Створюємо власний обробник, передаючи йому наш callback
            handler_with_callback = lambda request, client_address, server: \
                SyslogUDPHandler(request, client_address, server, self.message_handler_callback)

            self.server = socketserver.UDPServer((self.host, self.port), handler_with_callback)

            # Запускаємо сервер в окремому потоці, щоб не блокувати основний
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True  # Дозволяє основному потоку завершитися, навіть якщо цей потік ще працює
            self.thread.start()
            print(f"Syslog UDP Listener started successfully. Listening for messages...")
        except Exception as e:
            self.server = None
            print(f"Error starting Syslog UDP Listener: {e}")
            # Можна кинути виняток далі, якщо потрібно

    def stop(self):
        if self.server:
            print("Stopping Syslog UDP Listener...")
            self.server.shutdown()  # Зупиняє serve_forever
            self.server.server_close()  # Закриває сокет
            if self.thread:
                self.thread.join(timeout=5)  # Чекаємо завершення потоку
            self.server = None
            self.thread = None
            print("Syslog UDP Listener stopped.")
        else:
            print("Syslog UDP Listener is not running.")


# Простий тест для запуску слухача
if __name__ == '__main__':
    listener = SyslogUDPListener(host="0.0.0.0",
                                 port=514)  # Використовуємо інший порт для тесту, щоб не потрібні були sudo права
    try:
        listener.start()
        # Тримаємо основний потік живим, поки слухач працює
        # В реальному застосунку це буде керуватися головним сервісом
        while True:
            pass
    except KeyboardInterrupt:
        print("Shutdown requested by user...")
    finally:
        listener.stop()