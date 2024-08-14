from skpy import Skype
import os
from dotenv import load_dotenv
from skpy import SkypeEventLoop, SkypeNewMessageEvent
from icmplib import ping
import subprocess
import speedtest  # Nhập thư viện speedtest

load_dotenv()

username_skp = os.getenv('SKYPE_USER')
password_skp = os.getenv('SKYPE_PWD')

# Load hosts from environment variables
hosts = {
    'vnpt': os.getenv('vnpt'),
    'viettel': os.getenv('viettel'),
    'node1': os.getenv('node1'),
    'cisco': os.getenv('cisco'),
    'app': os.getenv('app'),
    'pbx': os.getenv('pbx')
}
# Debugging print statements
print(f"Username: {username_skp}, Password: {password_skp}")
print(f"Hosts to ping: {hosts}")

class SkypeListener(SkypeEventLoop):
    "Listen to a channel continuously"
    def __init__(self):
        try:
            super(SkypeListener, self).__init__(username_skp, password_skp)
        except Exception as e:
            print(f"Error during Skype login: {e}")
            return
        self.groupId = "19:d63482d4e9df41ff811e2fbc4d952447@thread.skype"
        self.Group = self.chats[self.groupId]

        self.Group.sendMsg("I'm listening...")

    def onEvent(self, event):
        print("onEvent called with event:", event)  # Debug statement

        if isinstance(event, SkypeNewMessageEvent):
            if event.msg.chatId == self.groupId:
                message_content = event.msg.content.lower()

                                
                if message_content == "ping all":
                    results = self.ping_all_hosts()
                    event.msg.chat.sendMsg(results)

                elif message_content.startswith("tracert "):
                    host_name = message_content.split(" ", 1)[1]
                    if host_name in hosts:
                        host = hosts[host_name]
                        results = self.tracert_host(host)
                        event.msg.chat.sendMsg(results)
                    # else:
                    #     event.msg.chat.sendMsg(f"Unknown host: {host_name}. Available hosts: {', '.join(hosts.keys())}")

                elif message_content.startswith("ping "):
                    host_name = message_content.split(" ", 1)[1]
                    if host_name in hosts:
                        host = hosts[host_name]
                        results = self.ping_single_host(host)
                        event.msg.chat.sendMsg(results)
                    else:
                        event.msg.chat.sendMsg(f"Unknown host: {host_name}. Available hosts: {', '.join(hosts.keys())}")

                elif message_content.startswith("speed test"):
                    self.Group.sendMsg("Testing...")
                    results = self.speed_test()
                    event.msg.chat.sendMsg(results)

                elif message_content == "hello":
                    self.Group.sendMsg("Hello ! I'm IT Support...")
                
                elif message_content == "list hosts":
                # Tạo danh sách các host với địa chỉ IP
                    host_list = "\n".join([f"{name}: {host}" for name, host in hosts.items()])
                    self.Group.sendMsg(f"List of hosts:\n{host_list}")  # Gửi tin nhắn với danh sách host

    def ping_all_hosts(self):
        results = []
        for name, host in hosts.items():
            print(f"Pinging {name} ({host})...")  # Debug statement
            self.Group.sendMsg("Pinging...")
            results.append(self.ping_single_host(host))
        return "\n".join(results)

    def ping_single_host(self, host):
        try:
            print(f"Pinging {host}...")  # Debug statement
            self.Group.sendMsg("Pinging...")
            response = ping(host, count=4, timeout=2)
            if response.is_alive:
                return f"{host} is reachable, avg round-trip time: {response.avg_rtt:.2f} ms"
            else:
                return f"{host} is not reachable."
        except Exception as e:
            return f"Error pinging {host}: {e}"
    def tracert_host(self, host):
        try:
            print(f"Tracing route to {host}...")  # Debug statement
            self.Group.sendMsg("Tracing...")
            # Use subprocess to run the tracert command
            result = subprocess.run(['tracert', host], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Tracert result for {host}:\n{result.stdout}"
            else:
                return f"Tracert failed for {host}:\n{result.stderr}"
        except Exception as e:
            return f"Error performing tracert on {host}: {e}"
        
    def speed_test(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()  # Tìm máy chủ tốt nhất
            download_speed = st.download() / 1_000_000  # Chuyển đổi từ bps sang Mbps
            upload_speed = st.upload() / 1_000_000  # Chuyển đổi từ bps sang Mbps
            ping_result = st.results.ping
            
            return (f"Download speed: {download_speed:.2f} Mbps\n"
                    f"Upload speed: {upload_speed:.2f} Mbps\n"
                    f"Ping: {ping_result:.2f} ms")
        except Exception as e:
            return f"Error performing speed test: {e}"

if __name__ == "__main__":
    my_skype = SkypeListener()
    my_skype.loop()
