import collections
import logging
import time
from datetime import datetime
import os
from argparse import ArgumentParser
from dateutil.relativedelta import relativedelta

from utils import  to_file, delete_file, monitor_nowtime


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
    parser.add_argument('--check-docker',help='Check pid that run in docker.',default=True)
    parser.add_argument('--docker-as-user',help='Whether use docker name as user name,if true,docker name must be ${USER}_xxx',default=True)

    args=parser.parse_args()
    docker_as_user=args.docker_as_user
    check_docker=args.check_docker
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
    # start=time.clock()
    # monitor_nowtime(is_console)
    # monitor_used_time=time.clock()-start
    # if is_console:
    #     logging.info('monitor used time:{}'.format(monitor_used_time))
    monitor_interval=args.monitor_interval
    used_message_list=[]
    while True:
        start = time.clock()

        now_time=datetime.now()
        if now_time.day-today.day==args.save_interval:
        # 新的一天，记录
            if is_console:
                logging.info('Date {},writing to file'.format(today.strftime('%Y-%m-%d')))

            to_file(used_message_list,
                    monitor_interval=monitor_interval,
                    save_dir= log_dir,
                    date=today.strftime('%Y-%m-%d'),
                    log_time_unit=log_time_unit,
                    docker_as_user=docker_as_user)
            today = now_time
            delete_file(log_dir,today+relativedelta(days=-log_storage_date),delete_summary)

        used_gpu_message=monitor_nowtime(is_console=is_console,check_docker=check_docker)
        used_message_list.extend(used_gpu_message)
        # to_file(used_message_list, monitor_interval, log_dir, today.strftime('%Y-%m-%d'), log_time_unit)

        time.sleep(monitor_interval-(time.clock()-start))

if __name__ == '__main__':
    main()

