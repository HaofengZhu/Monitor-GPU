import collections
import logging
import time
from datetime import datetime
import pandas as pd
import os
import subprocess
from argparse import ArgumentParser
from dateutil.relativedelta import relativedelta


def monitor_nowtime(is_console=False):
    command1 = 'nvidia-smi --query-compute-apps=pid,gpu_bus_id,used_gpu_memory --format=csv,nounits'
    df1 = pd.read_csv(os.popen(command1))
    command2 = 'nvidia-smi --query-gpu=index,pci.bus_id,memory.total --format=csv,nounits'
    df2 = pd.read_csv(os.popen(command2))
    now_time=datetime.now().strftime("%H:%M")
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

        used_gpu_message = [now_time,process_user_name,gpu_index, ratio]
        used_gpu_message_list.append(used_gpu_message)
    return used_gpu_message_list

def to_file(used_message_list,monitor_interval,save_dir,date,log_time_unit='hour'):
    used_message_list=pd.DataFrame(used_message_list,columns=['time(H:M)','user','gpu_index','ratio'])
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
    gpu_used={i:collections.defaultdict(int) for i in gpu_index}
    user_used_time_record=collections.defaultdict(list)
    for idx,used_message in used_message_list.iterrows():
        time, user_name, gpu_index, ratio=used_message
        if time not in user_used_time_record[user_name]:
            user_used_time_record[user_name].append(time)
        gpu_used[gpu_index][user_name]+=1*monitor_interval

    #记录每个用户使用的总时长，不管使用了多少GPU
    user_used_time={}
    for user_name,time in user_used_time_record.items():
        user_used_time[user_name]=len(time)*monitor_interval

    user_total_used=collections.defaultdict(int)
    for gpu_index,users_dict in gpu_used.items():
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


def main():
    logging.basicConfig(level=logging.INFO)
    is_console=True
    parser = ArgumentParser(description='Monitor GPU used.')
    parser.add_argument('--monitor-interval',help='monitor once per seconds,default is 60s.',default=60)
    parser.add_argument('--log-dir',help='dir for log file ,logging once a day',default='log')
    parser.add_argument('--log-time-unit',
                        help='time unit for logging summary file,default is hour',
                        choices=['day','hour','minute','second'],default='hour')
    parser.add_argument('--save-interval',help='save monitor logging to file interval,default is 1 day.',default=1)
    parser.add_argument('--log-storage-date',help='Max days to save log,default is 90 days.',default=90)
    parser.add_argument('--delete-summary',help='Delete summary or not,default is True.',default=True)

    args=parser.parse_args()
    log_dir=args.log_dir
    log_time_unit=args.log_time_unit
    log_storage_date=args.log_storage_date
    delete_summary=args.delete_summary
    if os.path.exists(log_dir):
        if is_console:
            logging.warn('log_dir exists')
    os.makedirs(log_dir,exist_ok=True)
    today = datetime.now()
    if is_console:
        logging.info('Start process time:{}'.format(today))
    start=time.clock()
    monitor_nowtime(is_console)
    monitor_used_time=time.clock()-start
    if is_console:
        logging.info('monitor used time:{}'.format(monitor_used_time))
    monitor_interval=args.monitor_interval
    used_message_list=[]
    while True:
        start = time.clock()

        now_time=datetime.now()
        if now_time.day-today.day==args.save_interval:
        # 新的一天，记录
            to_file(used_message_list, monitor_interval, log_dir, today.strftime('%Y-%m-%d'),log_time_unit)
            today = now_time
            delete_file(log_dir,today+relativedelta(days=-log_storage_date),delete_summary)

        used_gpu_message=monitor_nowtime(is_console)
        used_message_list.extend(used_gpu_message)

        time.sleep(monitor_interval-(time.clock()-start))

if __name__ == '__main__':
    main()

