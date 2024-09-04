import requests
import re

def get_ip_info(query):
    url = f"http://ip-api.com/json/{query}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        ip_info = response.json()
        
        if ip_info['status'] == 'fail':
            return f"Error: {ip_info['message']}"
        
        return ip_info
    except requests.RequestException as e:
        return f"Request failed: {e}"
    

def format_ip_info(ip_info):
    message = (
        f"**Thông tin IP:** {ip_info['query']}\n"
        f"**Quốc gia:** {ip_info['country']} ({ip_info['countryCode']})\n"
        f"**Khu vực:** {ip_info['regionName']} ({ip_info['region']})\n"
        f"**Thành phố:** {ip_info['city']}\n"
        f"**Tọa độ:** {ip_info['lat']}, {ip_info['lon']}\n"
        f"**Múi giờ:** {ip_info['timezone']}\n"
        f"**Nhà cung cấp:** {ip_info['isp']}\n"
        f"**Tổ chức:** {ip_info['org']}\n"
        f"**AS:** {ip_info['as']}\n"
    )
    return message

def is_valid_ip(ip):
    pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    return re.match(pattern, ip) is not None


# def get_dns_info(hotsname)
#     url = f"https://networkcalc.com/api/dns/lookup/{hostname}"    

#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         dns_info = response.json()
        
#         if ip_info['status'] == 'fail':
#             return f"Error: {dns_info['message']}"
        
#         return ip_info
#     except requests.RequestException as e:
#         return f"Request failed: {e}"
    

# def format_dns_info(dns_info):
#     message = (
#         f"**Thông tin IP:** {ip_info['query']}\n"
#         f"**Quốc gia:** {ip_info['country']} ({ip_info['countryCode']})\n"
#         f"**Khu vực:** {ip_info['regionName']} ({ip_info['region']})\n"
#         f"**Thành phố:** {ip_info['city']}\n"
#         f"**Tọa độ:** {ip_info['lat']}, {ip_info['lon']}\n"
#         f"**Múi giờ:** {ip_info['timezone']}\n"
#         f"**Nhà cung cấp:** {ip_info['isp']}\n"
#         f"**Tổ chức:** {ip_info['org']}\n"
#         f"**AS:** {ip_info['as']}\n"
#     )
#     return message