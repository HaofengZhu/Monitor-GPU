# Monitor GPU
Python脚本，用于记录服务器中谁使用了GPU，使用了多长时间并生成汇总报告。

## Monitor GPU Use
监控GPU使用记录，每隔一定时间记录一次GPU使用情况
```
pthon3 monitor.py [--monitor-interval ${MONITOR_INTERVAL}] [--log-dir ${LOG_DIR}] [--log-time-unit ${LOG_TIME_UNIT}] 
                    [--save-interval ${SAVE_INTERVAL}] [--log-storage-date ${LOG_STORAGE_DATE}]
                     [--delete-summary ${DELETE_SUMMARY}]
```
可选参数：
- `MONITOR_INTERVAL`:监控间隔（秒），每`MONITOR_INTERVAL`秒监控一次GPU使用情况，默认60秒，默认该时间段内用户一直在使用GPU
- `LOG_DIR`:日志存放的文件夹，默认`log`
- `LOG_TIME_UNIT`:日志中记录的用户使用时常的单位，可选`['day','hour','minute','second']`,默认`hour`
- `SAVE_INTERVAL`:每次写入日志的间隔（天），默认为1天，每次会写入两个日志：detail和summary，
        日志格式为`${DATE}_detail.csv`和`${DATE}_summary.csv`，detail日志保存了每个监控间隔记录到的用户名，
        使用的gpu_index，以及GPU使用率。summary日志记录这一天每个用户使用的总GPU时常（total gpu time(`LOG_TIME_UNIT`)），
        总时常（used time(`LOG_TIME_UNIT`)）以及平均GPU使用数量（average used gpu num）。
        其中，总GPU时常为使用的GPU数量*每个GPU使用的时常，总时常为占用GPU时常，无论占用了多少个GPU。平均GPU使用数量为总GPU时常/总时常。
- `LOG_STORAGE_DATE`:日志的保存时间（天），超过保存时间的日志会被删除，默认为90天
- `DELETE_SUMMARY`:是否删除summary日志，默认True
## Generate Report
根据监控记录生成一段时间的汇总报告
```
pthon3 generate_report.py [--start-date ${START_DATE}] [--end-date ${END_DATE}] [--log-dir ${LOG_DIR}] [--report-dir ${REPORT_DIR}]
```
可选参数：
- `START_DATE`:报告生成的开始时间，默认是`END_DATE`的一个月前
- `END_DATE`:报告生成的结束时间，默认是昨天
- `LOG_DIR`:日志存放的文件夹，默认`log`
- `REPORT_DIR`:报告存放的文件夹，默认`report`

## 注意
1. `generate_report.py`中不能应对多种`LOG_TIME_UNIT`的日志，不然会出现错误
2. 启动`monitor.py`如果`LOG_DIR`存在，会发送警告，但不会检查目录里面的文件是否安全有效
3. 该脚本不能放在容器中运行，不然会找不到使用GPU的进程号的信息


