import collections
from datetime import datetime
import logging
import subprocess
import pandas as pd
import os


def monitor_nowtime(is_console=False,check_docker=False):
    command1 = 'nvidia-smi --query-compute-apps=pid,gpu_bus_id,used_gpu_memory --format=csv,nounits'
    df1 = pd.read_csv(os.popen(command1))
    command2 = 'nvidia-smi --query-gpu=index,pci.bus_id,memory.total --format=csv,nounits'
    df2 = pd.read_csv(os.popen(command2))
    now_time=datetime.now().strftime("%H:%M")
    if is_console:
        logging.info('monitor on:%s' % datetime.now().strftime("'%Y-%m-%d %H:%M"))

    used_gpu_message_list=[]
    for idx, row in df1.iterrows():
        pid = row.loc['pid']
        if is_console:
            logging.info('test process:%s' % pid)
        # 下列执行命令行方法可以避免 can`t open file 错误
        p1 = subprocess.Popen(["ps", "-eo", "euser,pid"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["grep", '\s' + str(pid)], stdin=p1.stdout, stdout=subprocess.PIPE)
        p3 = subprocess.Popen(["cut", "-c", "1-6"], stdin=p2.stdout, stdout=subprocess.PIPE)
        process_user_name = p3.communicate()[0].decode()  # 得到进程执行人名
        names = process_user_name.split('\n')

        p4 = subprocess.Popen(["ps", "aux"], stdout=subprocess.PIPE)
        p5 = subprocess.Popen(["grep", '\s' + str(pid) + '\s'], stdin=p4.stdout, stdout=subprocess.PIPE)
        process_info = p5.communicate()[0]

        if not process_info:  # 未查到进程信息：
            continue
        for name in names:
            if not name:
                continue
            else:
                process_user_name = name.strip()
                break
        if not process_user_name:  # 未匹配到执行人
            continue
        if is_console:
            logging.info('user name:%s' % process_user_name)
        gpu_index = df2.loc[df2[df2[' pci.bus_id'] == row[' gpu_bus_id']].index.tolist()[0], 'index']
        if is_console:
            logging.info('GPU index:%s' % gpu_index)
        used_memory = row[' used_gpu_memory [MiB]']
        if is_console:
            logging.info('used gpu memory：%s MB' % used_memory)
        # print(df2[df2[' pci.bus_id'] == row[' gpu_bus_id']])
        gpu_memory = df2.loc[df2[df2[' pci.bus_id'] == row[' gpu_bus_id']].index.tolist()[0], ' memory.total [MiB]']
        ratio = float(used_memory) / float(gpu_memory) * 100
        if is_console:
            logging.info("used gpu memory rate:%.3f %%" % ratio)

        if check_docker:
            pid_to_docker_id=get_docker_pid()
            if pid in pid_to_docker_id:
                docker_name=pid_to_docker_id[pid]['name']
            else:
                docker_name=''
        else:
            docker_name=''

        used_gpu_message = [now_time,process_user_name,pid,docker_name,gpu_index, ratio]
        used_gpu_message_list.append(used_gpu_message)
    return used_gpu_message_list

def to_file(used_message_list,monitor_interval,save_dir,date,log_time_unit='hour',
            docker_as_user=False,docker_name_logo="&DOCKER&"):
    used_message_list=pd.DataFrame(used_message_list,
                                   columns=['time(H:M)','user','pid','container_name','gpu_index','ratio'])
    used_message_list.to_csv(os.path.join(save_dir,'{}_detail.csv'.format(date)),index=False,float_format='%.3f')
    time_unit=1
    if log_time_unit=='minute':
        time_unit=60
    if log_time_unit=='hour':
        time_unit=60*60
    if log_time_unit=='day':
        time_unit=60*60*24

    #总结
    command2 = 'nvidia-smi --query-gpu=index,pci.bus_id,memory.total --format=csv,nounits'
    df2 = pd.read_csv(os.popen(command2))
    gpu_index=list(df2['index'])

    #记录每个gpu，每个用户使用时常。
    gpu_used_time={i:collections.defaultdict(int) for i in gpu_index}
    #该用户在这里出现过一次就记录
    #把docker_name也当成user记录到summary里
    user_used_time_record=collections.defaultdict(list)
    docker_name_used_time_record=collections.defaultdict(list)

    user_used_time_gpu_index_record=collections.defaultdict(list)
    docker_name_used_time_gpu_index_record=collections.defaultdict(list)
    for idx,used_message in used_message_list.iterrows():
        time,user_name,pid,docker_name,gpu_index,ratio=used_message
        if docker_name!='':
            if docker_as_user:
                docker_name=docker_name.split('_')[0]
            else:
                docker_name=docker_name_logo+docker_name
        if time not in user_used_time_record[user_name]:
            user_used_time_record[user_name].append(time)
            #如果check_docker==False,docker_name==''
        if time not in docker_name_used_time_record[docker_name] and docker_name!='':
            docker_name_used_time_record[docker_name].append(time)

        time_gpu_index_str='{}_{}'.format(time,gpu_index)
        if time_gpu_index_str not in user_used_time_gpu_index_record[user_name]:
            #记录该用户某个gpu_index在某个time中已经使用了，避免一个用户在一个time里用同一个gpu跑了多个进程。
            user_used_time_gpu_index_record[user_name].append(time_gpu_index_str)
            gpu_used_time[gpu_index][user_name]+=1*monitor_interval
        if time_gpu_index_str not in docker_name_used_time_gpu_index_record[docker_name] and docker_name!='':
            #记录该用户某个gpu_index在某个time中已经使用了，避免一个用户在一个time里用同一个gpu跑了多个进程。
            docker_name_used_time_gpu_index_record[docker_name].append(time_gpu_index_str)
            gpu_used_time[gpu_index][docker_name]+=1*monitor_interval

    #记录每个用户使用的总时长，不管使用了多少GPU
    user_used_time={}
    for user_name,time in user_used_time_record.items():
        user_used_time[user_name]=len(time)*monitor_interval
    for docker_name,time in docker_name_used_time_record.items():
        user_used_time[docker_name]=len(time)*monitor_interval

    user_total_used=collections.defaultdict(int)
    for gpu_index,users_dict in gpu_used_time.items():
        for user,time in users_dict.items():
            user_total_used[user]+=time
    output_dict=[]
    for user in user_total_used:
        output_dict.append([user,user_total_used[user]/time_unit,user_used_time[user]/time_unit,
                            user_total_used[user]/user_used_time[user]])
    output_dict=pd.DataFrame(output_dict,columns=['user','total gpu time({})'.format(log_time_unit),
                                                  'used time({})'.format(log_time_unit),'average used gpu num'])
    output_dict.to_csv(os.path.join(save_dir,'{}_summary.csv'.format(date)),index=False,float_format='%.3f')

def delete_file(log_dir,delete_date,delete_summary):
    dfiles=[]
    for file in os.listdir(log_dir):
        if file.find('summary')!=-1:
            type='summary'
        elif file.find('detail')!=-1:
            type='detail'
        else:
            continue
        date = file.split('_')[0]
        date = datetime.strptime(date, '%Y-%m-%d')
        if date<delete_date:
            if type=='summary' and delete_summary:
                dfiles.append(os.path.join(log_dir,file))
            else:
                dfiles.append(os.path.join(log_dir,file))
    for file in dfiles:
        os.remove(file)


def get_docker_pid():
    command1 = 'docker ps --format "{{.ID}},{{.Image}},{{.Names}}"'
    df1 = pd.read_csv(os.popen(command1), header=None)
    df1.columns = ['ID', 'Image', 'Names']
    docker_id_to_name={row['ID']:row['Names'] for i,row in df1.iterrows()}

    pid_to_docker_id = {}
    command2_templete = 'docker top {docker_id}'
    for docker_id in df1['ID']:
        s = os.popen(command2_templete.format(docker_id=docker_id))
        data = s.readlines()
        for line in data[1:]:
            arr = line.split(' ')
            new_arr = []
            for s in arr:
                if s != '':
                    new_arr.append(s)
            # new_arr前三个为['ID','PID','PPID']
            pid=int(new_arr[1])
            pid_to_docker_id[pid]={'id':docker_id,'name':docker_id_to_name[docker_id]}
    return pid_to_docker_id


