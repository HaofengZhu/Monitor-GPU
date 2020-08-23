import logging
import os
from argparse import ArgumentParser
from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta

def main():
    parser = ArgumentParser(description='Generate GPU used report.It will generate report form start date to end date.')
    parser.add_argument('--start-date', help='report start date,format is %Y-%m-%d,default is one month before end date', default=None)
    parser.add_argument('--end-date', help='report end date,default is the date before today', default=None)
    parser.add_argument('--log-dir',help='dir for log file',default='log')
    parser.add_argument('--report-dir',help='dir for report file',default='report')
    args=parser.parse_args()

    end_date=args.end_date
    start_date=args.start_date
    if end_date is None:
        end_date=datetime.today()+relativedelta(days=-1)
        end_date=datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0)
    else:
        end_date=datetime.strptime(end_date,'%Y-%m-%d')
    if start_date is None:
        start_date=end_date+relativedelta(months=-1)
    else:
        start_date=datetime.strptime(start_date,'%Y-%m-%d')

    log_dir=args.log_dir
    report_dir=args.report_dir
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    use_files=[]
    min_date=end_date
    max_date=start_date
    for file in os.listdir(log_dir):
        if file.find('summary')!=-1:
            date=file.split('_')[0]
            date=datetime.strptime(date,'%Y-%m-%d')
            if start_date<=date<=end_date:
                use_files.append(os.path.join(log_dir,file))
                if date<min_date:
                    min_date=date
                if date>max_date:
                    max_date=date
    if min_date!=start_date:
        logging.warn('Setting start date is {},but the earliest date found in log dir is {}'
                     .format(start_date.strftime('%Y-%m-%d'),min_date.strftime('%Y-%m-%d')))
    if max_date!=end_date:
        logging.warn('Setting end date is {},but the latest date found in log dir is {}'
                     .format(end_date.strftime('%Y-%m-%d'),max_date.strftime('%Y-%m-%d')))

    user_gpu_time={}
    columns_name=['user','total gpu time','used time','average used gpu num']
    df=None
    for file in use_files:
        df=pd.read_csv(file)
        for idx,line in df.iterrows():
            user,total_used_time,used_time,average_use_gpu=line
            if user not in user_gpu_time:
                user_gpu_time[user]=[0,0]
            user_gpu_time[user][0] += total_used_time
            user_gpu_time[user][1]+=used_time
    if df is not None:
        columns_name=df.columns.values

    output=[]
    for user,(total_used_time,used_time) in user_gpu_time.items():
        output.append([user,total_used_time,used_time,total_used_time/used_time])
    output=pd.DataFrame(output,columns=columns_name)
    output.sort_values(by=columns_name[1],ascending=False,inplace=True)
    output.to_csv(os.path.join(report_dir,'{}~{}_report.csv'
                               .format(min_date.strftime('%Y-%m-%d'),max_date.strftime('%Y-%m-%d')))
                  ,float_format='%.3f')


if __name__ == '__main__':
    main()



