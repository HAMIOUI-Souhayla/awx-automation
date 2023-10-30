import subprocess
import re
import paramiko
import yaml

def run_remote_sudo_l(server_ip):
    try:
        ssh_command = ['ssh', f'ubuntu@{server_ip}', 'sudo', '-l']
        output = subprocess.check_output(ssh_command, universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'sudo -l' on server {server_ip}: {e}")
        return None

def parse_sudo_output(output):
    user_pattern = r'(?<=for )\w+'
    command_pattern = r'\((\w+)\) NOPASSWD: (\S+)'
    user_matches = re.findall(user_pattern, output)
    command_matches = re.findall(command_pattern, output)
    if not user_matches or not command_matches:
        return None
    user = user_matches[0]
    commands = [match[1] for match in command_matches]
    return {'user': user, 'commands': commands}

def write_command_file(commands, server_ip):
    try:
        filename = f"commands_missing_{server_ip}.txt"
        with open(filename, 'w') as file:
            for command in commands:
                file.write(f"{command}\n")
        print(f"Command file created for server {server_ip}.")
        return True
    except IOError as e:
        print(f"Error creating command file for server {server_ip}: {e}")
        return False

def load_yaml_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error loading YAML file '{file_path}': {e}")
        return None

def execute_script_on_remote_server(server_ip):
    try:
        ssh_command_output = run_remote_sudo_l(server_ip)
        if ssh_command_output:
            parsed_data = parse_sudo_output(ssh_command_output)
            if parsed_data:
                comparison_yaml_path = '/home/souhahm/testyaml.yaml'
                comparison_yaml_data = load_yaml_file(comparison_yaml_path)
                if comparison_yaml_data:
                    comparison_commands = comparison_yaml_data[0].get('vars', {}).get('commands', [])
                    unique_commands = list(set(comparison_commands) - set(parsed_data['commands']))
                    if unique_commands:
                        write_command_file(unique_commands, server_ip)
                else:
                    print(f"Failed to load comparison YAML file on server {server_ip}.")
            else:
                print(f"Failed to parse sudo output on server {server_ip}.")
        else:
            print(f"Failed to execute 'sudo -l' on server {server_ip}.")
    except paramiko.SSHException as e:
        print(f"Error executing script on server {server_ip}: {e}")

original_script = """
import subprocess
import re

def get_ip_addresses():
    try:
        output = subprocess.check_output(['ip', 'a'], universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'ip a': {e}")
        return None

def parse_ip_addresses(output):
    interfaces = []
    current_interface = None

    lines = output.split('\\n')
    for line in lines:
        if re.match(r"^\d+:\s+(\w+):", line):
            if current_interface is not None:
                interfaces.append(current_interface)
            interface_name = re.search(r"^\d+:\s+(\w+):", line).group(1)
            current_interface = {'name': interface_name, 'config': []}
        elif re.match(r"\\s+inet\\s+(\d+\\.\\d+\\.\\d+\\.\\d+/\\d+)", line):
            ip_address = re.search(r"\\s+inet\\s+(\d+\\.\\d+\\.\\d+\\.\\d+\\/\\d+)", line).group(1)
            current_interface['config'].append(ip_address)
            broadcast_address = re.search(r"\\s+brd\\s+(\d+\\.\\d+\\.\\d+\\.\\d+)", line)
            if broadcast_address:
                current_interface['config'].append(f"Broadcast: {broadcast_address.group(1)}")

    if current_interface is not None:
        interfaces.append(current_interface)

    return interfaces

def write_output_file(interfaces):
    with open('ip_addresses_output.txt', 'w') as file:
        for interface in interfaces:
            file.write(f"Interface: {interface['name']}\\n")
            for config in interface['config']:
                file.write(f"{config}\\n")
            file.write('\\n')

if _name_ == "_main_":
    ip_addresses_output = get_ip_addresses()
    if ip_addresses_output:
        parsed_interfaces = parse_ip_addresses(ip_addresses_output)
        write_output_file(parsed_interfaces)
        print("IP addresses and broadcast addresses written to 'ip_addresses_output.txt'.")
    else:
        print("Failed to get IP addresses.")
"""

def execute_remote_script(server_ip, script_content, local_output_dir):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username='ubuntu')

        remote_filename = 'remote_script.py'
        with ssh.open_sftp().file(remote_filename, 'w') as remote_file:
            remote_file.write(script_content)

        stdin, stdout, stderr = ssh.exec_command(f'python {remote_filename}')
        script_output = stdout.read().decode()

        ssh.close()

        return script_output

    except paramiko.SSHException as e:
        print(f"Error executing script on server {server_ip}: {e}")
        return None

if _name_ == "_main_":
    remote_ips_first_check = ['127.0.0.1']
    remote_ips_second_check = ['127.0.0.1']
    local_output_dir = '/home/souhahm'

    for remote_ip in remote_ips_first_check:
        execute_script_on_remote_server(remote_ip)

    for remote_ip in remote_ips_second_check:
        script_output = execute_remote_script(remote_ip, original_script, local_output_dir)
        if script_output:
            output_filename = f'ip_addresses_output_{remote_ip}.txt'
            with open(f'{local_output_dir}/{output_filename}', 'w') as local_file:
                local_file.write(script_output)
    print("Script execution on remote servers completed.")
