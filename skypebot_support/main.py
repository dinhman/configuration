from skpy import Skype
import os
from dotenv import load_dotenv
from skpy import SkypeEventLoop, SkypeNewMessageEvent
from icmplib import ping
import subprocess
import speedtest  # Nhập thư viện speedtest
import requests
from ports import load_ports, find_port_info
from http_utils import load_http_codes, get_http_code_info 
from email_utils import send_email
from database import insert_user, delete_user
from ip import get_ip_info, format_ip_info

http_data = load_http_codes('http.codes.json') 
load_dotenv()

username_skp = os.getenv('SKYPE_USER')
password_skp = os.getenv('SKYPE_PWD')
skype_group = os.getenv('SKYPE_GROUP')
# Load hosts from environment variables
hosts = {
    'vnpt': os.getenv('vnpt'),
    'viettel': os.getenv('viettel'),
    'node1': os.getenv('node1'),
    'cisco': os.getenv('cisco'),
    'app': os.getenv('app'),
    'pbx': os.getenv('pbx')
}

print("I'm listening !")

class SkypeListener(SkypeEventLoop):
    "Listen to a channel continuously"
    def __init__(self):
        try:
            super(SkypeListener, self).__init__(username_skp, password_skp)
        except Exception as e:
            print(f"Error during Skype login: {e}")
            return
        self.groupId = skype_group
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
            

                elif message_content.startswith("ping "):
                    host_name = message_content[len("ping "):].strip()  # Lấy tên host từ tin nhắn
                    results = self.ping_single_host(host_name)  # Gọi hàm ping
                    event.msg.chat.sendMsg(results)  # Gửi kết quả ping về nhóm

                elif message_content.startswith("speed test"):
                    self.Group.sendMsg("Testing...")
                    results = self.speed_test()
                    event.msg.chat.sendMsg(results)

                elif message_content.startswith("my ip"):
                    ip_address = self.get_public_ip()
                    self.Group.sendMsg(f"Your public IP address is: {ip_address}")
                
            # Kiểm tra port
                elif message_content.startswith("check port "):
                    port_number = message_content[len("check port "):].strip()  # Lấy số port
                    if port_number.isdigit():
                        data = load_ports("ports.lists.json")  # Load dữ liệu từ file JSON
                        port_info = find_port_info(data, port_number)  # Tìm kiếm thông tin port
                        if port_info:
                            response = (f"Port: {port_info['port']}\n"
                                        f"Mô tả: {port_info['description']}\n"
                                        f"UDP: {port_info['udp']}\n"
                                        f"Trạng thái: {port_info['status']}\n"
                                        f"TCP: {port_info['tcp']}")
                        else:
                            response = f"Không tìm thấy thông tin cho port: {port_number}"
                    else:
                        response = "Vui lòng nhập một số port hợp lệ."
                    event.msg.chat.sendMsg(response)

                elif message_content.startswith("check http code "):
                    code_key = message_content[len("check http code "):].strip()  # Lấy mã từ tin nhắn
                    message, description = get_http_code_info(http_data, code_key)  # Trích xuất thông tin
                    if message:
                        self.Group.sendMsg(f"Mã: {code_key}\n Nội dung: {message}\n Mô tả: {description}")
                    else:
                        self.Group.sendMsg(f"Mã {code_key} không có trong file JSON.")

                elif message_content == "random pass":
                    password = self.random_password()
                    self.Group.sendMsg(f"Mật khẩu ngẫu nhiên của bạn: {password}")



                elif message_content == "list hosts":
                # Tạo danh sách các host với địa chỉ IP
                    host_list = "\n".join([f"{name}: {host}" for name, host in hosts.items()])
                    self.Group.sendMsg(f"List of hosts:\n{host_list}")  # Gửi tin nhắn với danh sách host

                elif message_content == "it tools":       
                    self.Group.sendMsg("Check more IT tools in https://it-tools.tech/")

                elif message_content.startswith("send email"):
                    try:
                        # Tách thông tin từ tin nhắn
                        lines = message_content.split("\n")
                        to_email = ""
                        subject = ""
                        body = ""

                        for line in lines:
                            if line.startswith("to:"):
                                to_email = line[len("to:"):].strip()  # Lấy địa chỉ email
                            elif line.startswith("sub:"):
                                subject = line[len("sub:"):].strip()  # Lấy chủ đề email
                            elif line.startswith("mess:"):
                                body = line[len("mess:"):].strip()  # Lấy nội dung email

                        # Gửi email nếu tất cả thông tin đã được cung cấp
                        if to_email and subject and body:
                            send_email(subject, body, to_email)  # Gọi hàm gửi email
                            event.msg.chat.sendMsg("Email đã được gửi thành công!")  # Gửi thông báo thành công
                        else:
                            event.msg.chat.sendMsg("Vui lòng cung cấp đầy đủ thông tin (to, sub, mess).")

                    except Exception as e:
                        event.msg.chat.sendMsg(f"Đã xảy ra lỗi khi gửi email: {e}")

                elif message_content.startswith("insert "):
                    if event.msg.userId == "live:.cid.cf69b44f1c253509":
                        try:
                            # Tách thông tin từ tin nhắn
                            parts = message_content[len("insert "):].strip().split(",")
                            
                            # Kiểm tra số lượng phần tử trong parts
                            if len(parts) < 4:
                                raise ValueError("Vui lòng cung cấp đầy đủ thông tin: tên người dùng, Skype ID, GetSMS và DCA.")
                            
                            # Tách tên người dùng và Skype ID
                            crm_user = parts[0].strip()  # Tên người dùng
                            skype_user = parts[1].strip()  # Skype ID
                            
                            # Chuyển đổi GetSMS từ chuỗi sang số nguyên
                            try:
                                get_sms = int(parts[2].strip())  # GetSMS
                            except ValueError:
                                raise ValueError("GetSMS phải là một số nguyên.")
                            
                            dca = parts[3].strip()  # DCA

                            # Gọi hàm chèn người dùng
                            result = insert_user(crm_user, skype_user, get_sms, dca)
                            event.msg.chat.sendMsg(result)  # Gửi thông báo thành công
                        except Exception as e:
                            event.msg.chat.sendMsg(f"Đã xảy ra lỗi: {e}")
                    else:
                        event.msg.chat.sendMsg("Bạn không có quyền insert users !")

                elif message_content.startswith("delete user "):
                    if event.msg.userId == "live:.cid.cf69b44f1c253509":
                        try:
                            # Tách tên người dùng từ tin nhắn
                            crm_user = message_content[len("delete user "):].strip()  # Tên người dùng
                            
                            # Kiểm tra nếu tên người dùng không rỗng
                            if not crm_user:
                                raise ValueError("Tên người dùng không được để trống.")

                            # Gọi hàm xóa người dùng
                            result = delete_user(crm_user)
                            event.msg.chat.sendMsg(result)  # Gửi thông báo thành công
                        except Exception as e:
                            event.msg.chat.sendMsg(f"Đã xảy ra lỗi: {e}")
                    else:
                        event.msg.chat.sendMsg("Bạn không có quyền delete users !")

                elif message_content.startswith("check ip "):
                    try:
                        # Extract the IP query from the message
                        ip_query = message_content[len("check ip "):].strip()
                        
                        # Optionally, you can validate the IP format here if needed
                        
                        # Get the IP information
                        ip_info = get_ip_info(ip_query)
                        ip_info_message = format_ip_info(ip_info)

                        #Send the IP information back as a message
                        event.msg.chat.sendMsg(str(ip_info_message))  # Convert the dictionary to a string for sending
                    except Exception as e:
                        event.msg.chat.sendMsg(f"Đã xảy ra lỗi: {e}")

                elif message_content == "trung": 
                    self.Group.sendMsg("Tất nhiên là Phương rồi <3")
                
                elif message_content.startswith("help"):
                    self.Group.sendMsg(
                        "Hello! Xin vui lòng xem các keyword có thể sử dụng:\n"
                        "1. ping / tracert + {IP}\n"                    
                        "2. check port + {port}\n"
                        "3. check http code + {code}\n"
                        "4. check ip + {ip/hostname}\n"
                        "5. insert {crm_user, skype_user, get_sms, dca} / delete {crm_user}\n"
                        "5. send email \n"
                        "to: \n"
                        "sub: \n"
                        "mess: \n"
                        "6. speed test, random pass, my ip, it tools,...\n"
                        "\n"
                        "___updated 15.08.2024"
                    )

                elif message_content == "hello" or message_content == "hi":
                    self.Group.sendMsg("Hello! I'm IT Support...")

                


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
        
    def get_public_ip(self):
        try:
            response = requests.get("https://api.ipify.org?format=json")
            response.raise_for_status()  # Kiểm tra lỗi HTTP
            ip_data = response.json()
            
            print(f"Received JSON response: {ip_data}")  # Debug line
            
            return ip_data["ip"]  # Trả về địa chỉ IP
        except requests.exceptions.RequestException as e:
            return f"Error retrieving public IP: {e}"
        
    def random_password(self):
        url = "https://api.api-ninjas.com/v1/passwordgenerator"
        headers = {
            "X-Api-Key": "WaLCyspzoUafs0q/8l8M2w==WyGcirotAv61xw1W"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Kiểm tra lỗi HTTP
            password_data = response.json()
            return password_data.get('random_password', 'Không thể tạo mật khẩu.')
        except requests.exceptions.RequestException as e:
            return f"Error generating password: {e}"
            
if __name__ == "__main__":
    my_skype = SkypeListener()
    my_skype.loop()
