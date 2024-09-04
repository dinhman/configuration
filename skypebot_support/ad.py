import re
import subprocess



def process_message(self, message):
    match = re.match(r'create ad (\w+) (\w+) (\w+) (\w+)', message)
    if match:
        first_name = match.group(1)
        last_name = match.group(2)
        title = match.group(3)
        group_name = match.group(4)
        self.create_ad_user(first_name, last_name, title, group_name)
    else:
        print("Tin nhắn 'create ad' không đúng định dạng.")

def create_ad_user(self, first_name, last_name, title, group_name):
    username = f"{first_name.lower()}.{last_name.lower()}"
    password = "ABCabc123@"  # Thay đổi mật khẩu nếu cần
    ou_path = "OU=Users,DC=yourdomain,DC=com"  # Thay đổi OU nếu cần

    powershell_command = f"""
    New-ADUser -Name "{first_name} {last_name}" `
                -GivenName "{first_name}" `
                -Surname "{last_name}" `
                -SamAccountName "{username}" `
                -UserPrincipalName "{username}@mandinh.click" `
                -Path "{ou_path}" `
                -AccountPassword (ConvertTo-SecureString "{password}" -AsPlainText -Force) `
                -Enabled $true `
                -Title "{title}"
    Add-ADGroupMember -Identity "{group_name}" -Members "{username}"
    """

    try:
        process = subprocess.Popen(["powershell", "-Command", powershell_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"User {username} created successfully with title {title} and added to group {group_name}.")
        else:
            print(f"Error creating user: {stderr.decode()}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

