# Shree KRISHNAya Namaha
# Prints which of the AWS GPU cards are available.
# Author: Nagabhushan S N
# Last Modified: 24/05/2024

import datetime
import time
import traceback
from pathlib import Path

import paramiko

this_filepath = Path(__file__)
this_filename = this_filepath.stem


def get_free_gpu_cards(name: str, ip: str, username: str, key_filepath: Path):
    # create a SSH client object
    ssh = paramiko.SSHClient()
    # TODO: need to secure the below line following https://stackoverflow.com/a/43093883/3337089
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # connect to the remote host https://stackoverflow.com/a/8417181/3337089
    ssh.connect(hostname=ip, username=username, key_filename=key_filepath.as_posix())

    # define the commands to run
    command1 = 'nvidia-smi --query-gpu=memory.free --format=csv'
    # execute the command on the remote host
    stdin, stdout, stderr = ssh.exec_command(command1)
    # read the output from the command
    output = stdout.read().decode()
    lines = output.split('\n')[1:-1]
    mem_free = [int(line.split(' ')[0]) for line in lines]

    # define the commands to run
    command2 = 'nvidia-smi --query-gpu=memory.total --format=csv'
    # execute the command on the remote host
    stdin, stdout, stderr = ssh.exec_command(command2)
    # read the output from the command
    output = stdout.read().decode()
    lines = output.split('\n')[1:-1]
    total_mems = [int(line.split(' ')[0]) for line in lines]

    # define the commands to run
    command3 = 'nvidia-smi --query-gpu=utilization.gpu --format=csv'
    # execute the command on the remote host
    stdin, stdout, stderr = ssh.exec_command(command3)
    # read the output from the command
    output = stdout.read().decode()
    lines = output.split('\n')[1:-1]
    utils = [int(line.split(' ')[0]) for line in lines]

    num_free_cards = 0
    free_cards = ''
    for i in range(len(mem_free)):
        if (mem_free[i]/total_mems[i] > 0.5) and (utils[i] < 50):
            num_free_cards += 1
            free_cards += f'{name} ({ip}) Card {i}: Available Memory {mem_free[i]}/{total_mems[i]}; GPU Utilization {utils[i]}%\n'
    # close the SSH connection
    ssh.close()
    return num_free_cards, free_cards


def print_all_free_gpus():
    username = 'nagabhushan'
    key_filepath = Path('/Users/nagabhushan/SpreeAI/Docs/Softwares/AWS/AWS_Nagabhushan_RSA')
    machines = {
        'ML-15': '10.2.101.223',
        'ML-14': '10.2.87.134',
        'ML-13': '10.2.94.212',
        'ML-12': '10.2.90.61',
        'ML-11': '10.2.80.234',
        'ML-10': '10.2.98.31',
        'ML-09': '10.2.93.229',
        'ML-08': '10.2.92.231',
        'ML-07': '10.2.92.197',
        'ML-06': '10.2.95.234',
        'ML-05': '10.2.94.216',
        'ML-04': '10.2.81.86',
        'ML-03': '10.2.83.214',
        'ML-02': '10.2.84.221',
        'ML-01': '10.2.84.61',
    }

    free_gpus = 'The below GPUs are available:\n\n'
    for name, ip in machines.items():
        try:
            num_free_cards, free_cards = get_free_gpu_cards(name, ip, username, key_filepath)
            if num_free_cards > 0:
                print_text = f'{num_free_cards} cards available in {name} ({ip})\n' + free_cards
            else:
                print_text = f'No cards free in {name} ({ip})\n'
            free_gpus += free_cards
        except Exception:
            print_text = f'Unable to connect to {name} ({ip})\n'
            free_gpus += print_text
        print(print_text)
    return free_gpus


def demo1():
    # define the remote host and credentials
    host = '10.2.90.61'
    username = 'nagabhushan'
    key_filepath = Path('/Users/nagabhushan/Data/Work/SpreeAI/Docs/Softwares/AWS/AWS_Nagabhushan_PersonalLaptop_RSA')

    # create a SSH client object
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # connect to the remote host
    ssh.connect(hostname=host, username=username, key_filename=key_filepath.as_posix())

    # define the command to run
    command = 'nvidia-smi --query-gpu=memory.free --format=csv'

    # execute the command on the remote host
    stdin, stdout, stderr = ssh.exec_command(command)

    # read the output from the command
    output = stdout.read().decode()

    # print the output
    print(output)

    # close the SSH connection
    ssh.close()
    return


def demo2():
    print_all_free_gpus()
    return


def main():
    demo2()
    return


if __name__ == '__main__':
    print('Program started at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    start_time = time.time()
    try:
        main()
        run_result = 'Program completed successfully!'
    except Exception as e:
        print(e)
        traceback.print_exc()
        run_result = 'Error: ' + str(e)
    end_time = time.time()
    print('Program ended at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    print('Execution time: ' + str(datetime.timedelta(seconds=end_time - start_time)))
