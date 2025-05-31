# app/modules/data_ingestion/listeners/netflow_udp_collector.py
import socketserver
import threading


# Функція зворотного виклику (буде замінена методом з DataIngestionService)
def default_netflow_handler(raw_packet_bytes: bytes, client_address: tuple):
    print(
        f"NETFLOW/IPFIX packet received from {client_address[0]}:{client_address[1]}, size: {len(raw_packet_bytes)} bytes (via collector)")


class NetflowUDPHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server, message_handler_callback):
        self.message_handler_callback = message_handler_callback
        super().__init__(request, client_address, server)

    def handle(self):
        data = self.request[0]
        self.message_handler_callback(data, self.client_address)


class NetflowUDPCollector:
    def __init__(self, host: str = "0.0.0.0", port: int = 2055,
                 message_handler_callback=default_netflow_handler):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.message_handler_callback = message_handler_callback

    def start(self):
        if self.server:
            print("NetFlow UDP Collector is already running.")
            return
        print(f"Starting NetFlow UDP Collector on {self.host}:{self.port}...")
        try:
            handler_with_callback = lambda request, client_address, server: \
                NetflowUDPHandler(request, client_address, server, self.message_handler_callback)
            self.server = socketserver.UDPServer((self.host, self.port), handler_with_callback)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"NetFlow UDP Collector started successfully. Listening for packets...")
        except Exception as e:
            self.server = None
            print(f"Error starting NetFlow UDP Collector: {e}")

    def stop(self):
        if self.server:
            print("Stopping NetFlow UDP Collector...")
            self.server.shutdown()
            self.server.server_close()
            if self.thread and self.thread.is_alive():  # Перевірка, чи потік ще живий
                self.thread.join(timeout=5)
            self.server = None
            self.thread = None
            print("NetFlow UDP Collector stopped.")
        else:
            print("NetFlow UDP Collector is not running.")
