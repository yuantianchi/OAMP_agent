#!/usr/bin/env python
# !-*- coding:utf-8 -*-

from bin.base.log import PrintLog
import bin
from bin.base.tool import File, JsonFileFunc, Path
import threading
from bin.logic import Inner_logic
import time
from bin.base.tool import FuncRedisModifier
import os
from bin.base.tool import  Mail
from bin.base.tool import FuncRecordModifier

LogObj = PrintLog.getInstance()
jff = JsonFileFunc.getInstance()
p = Path.getInstance()
F = File.getInstance()


# 初始化配置文件到缓存中，创建项目更新文件存放目录
class Init(object):
    def __init__(self):
        self.confPath = p.confDirPath + os.sep + "conf.json"
        self.ProjectConfigPath = p.confDirPath + os.sep + "projectInfo.json"

    def rebuild_memory_val(self):
        bin.CONF_INFO = jff.readFile(self.confPath)
        bin.PROJECT_INFO = jff.readFile(self.ProjectConfigPath)

    def __reset_exec_func_state(self):
        if bin.CONF_INFO is not None and bin.CONF_INFO.get('redis') is not None and bin.PROJECT_INFO is not None:
            redis_info = bin.CONF_INFO.get('redis')
            for k in bin.PROJECT_INFO.keys():
                func_redis_ins = FuncRedisModifier.getInstance(redis_k=k, redis_info=redis_info).init_redis()
                if func_redis_ins is None:
                    continue
                func_redis_ins.set_func_state_start().set_redis()
            return True
        else:
            LogObj.error('启动项目功能执行，重置状态失败！！！！')
            Mail.getInstance().sendMail("OAMP_anget启动项目功能执行，重置状态失败！！！！")
            # 发邮件的！！！！ fixed 2019年1月22日14:55:04


    def exec(self):
        LogObj.info('%s 开始运行' % threading.current_thread().name)
        inner_logic_ins = Inner_logic.getInstance()
        if not self.__reset_exec_func_state():
            return 0
        while True:
            if bin.CONF_INFO is not None and bin.CONF_INFO.get('redis') is not None and bin.PROJECT_INFO is not None:
                redis_info = bin.CONF_INFO.get('redis')
                for k in bin.PROJECT_INFO.keys():
                    func_redis_ins = FuncRedisModifier.getInstance(redis_k=k, redis_info=redis_info).init_redis()
                    if func_redis_ins is None:
                        # LogObj.debug('%s项目暂无待执行的方法'% str(k))
                        continue

                    method = func_redis_ins.get_func_method()
                    func_state = func_redis_ins.get_func_state()
                    fun_summary = func_redis_ins.get_func_summary()
                    exec_count = func_redis_ins.get_func_exec_count()
                    opt_id = func_redis_ins.get_func_opt_id()

                    func_record_ins = FuncRecordModifier.getInstance(projectName=k)
                    func_record_ins.setOperateId(opt_id)

                    if exec_count > 3:
                        LogObj.error('%s项目，执行%s方法未成功超过3次,将结束执行' % (str(k), str(method)))
                        func_state = FuncRedisModifier.REDIS_FUNC_STATE_FAILED

                    if FuncRedisModifier.REDIS_FUNC_STATE_NONE == func_state:
                        LogObj.error('未正常实例化功能redis对象')
                        func_record_ins.setSummary('未正常实例化功能redis对象')
                        func_record_ins.setIs_normal(FuncRecordModifier.not_Normal)

                    elif FuncRedisModifier.REDIS_FUNC_STATE_RUN == func_state:
                        LogObj.debug('%s 项目正在执行%s 操作,相关操作描述为:%s' % (str(k), method, str(fun_summary)))
                        func_record_ins.setSummary('%s 项目正在执行%s 操作,相关操作描述为:%s' % (str(k), method, str(fun_summary)))

                    elif FuncRedisModifier.REDIS_FUNC_STATE_END == func_state:
                        LogObj.info('%s项目执行%s操作正常结束' % (str(k), method))
                        func_record_ins.setIs_finished(FuncRecordModifier.finished)
                        func_record_ins.setSummary('%s 项目正在执行%s 操作,相关操作描述为:%s' % (str(k), method, str(fun_summary)))
                        func_redis_ins.del_redis()

                    elif FuncRedisModifier.REDIS_FUNC_STATE_FAILED == func_state:
                        LogObj.error('%s项目执行%s操作失败，异常结束' % (str(k), method))
                        func_record_ins.setIs_finished(FuncRecordModifier.finished)
                        func_record_ins.setSummary('%s项目执行%s操作失败，异常结束' % (str(k), method))
                        func_record_ins.setIs_normal(FuncRecordModifier.not_Normal)
                        func_redis_ins.del_redis()

                    elif FuncRedisModifier.REDIS_FUNC_STATE_START == func_state:
                        t = threading.Thread(target=getattr(inner_logic_ins, method), args=(redis_info, k,))
                        func_record_ins.setSummary('%s项目即将进行%s 操作,相关操作描述为:%s' % (str(k), method, str(fun_summary)))
                        t.start()

                    else:
                        LogObj.error('功能redis对象非正常状态')
                        func_record_ins.setSummary('功能redis对象非正常状态')
                        func_record_ins.setIs_normal(FuncRecordModifier.not_Normal)

                    func_record_ins.set_FuncRecord()
                    # fixed 等待后续操作内容处理
                    # 修改执行结果内容
            time.sleep(3)

    # 初始化redis 方法接收者
    def init_redis_func_receiver(self):
        t = threading.Thread(target=self.exec, name='threadFuncReceiverTask', daemon=True)
        t.start()


def getInstance():
    return Init()