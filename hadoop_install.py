#!/usr/bin/python
# -*- coding: utf-8 -*-
# ***************************************************************************
# 程 序 名: hadoop_install.py
# 配置文件: hadoop_install.cfg
# 说    明: hadoop环境搭建及相关组件安装
# 创建时间：2016.09.30
# 更新时点：2016.12.18
# 更新内容：添加选项参数
#           hadoop_install.py -[cih] | -[adu] software_name
#               -c  ==> --clean
#               -i  ==> --install
#               -h  ==> --help
#               -a  ==> --add       software
#               -d  ==> --delete software
#               -u  ==> --update software
# 更新日期：2016.12.19
# 更新内容：添加hadoop-env.sh文件中JAVA_HOME环境变量
# 更新日期：2016.12.24
# 更新内容：添加函数解析安装软件名
#           例如：apache-hive-2.1.1-bin.tar.gz
#           hadoop-2.7.2.tar.gz
# 更新日期：2017.01.30
# 更新内容：调整/etc/profile.d目录下生成的配置脚本为多行输出
# 更新日期：2017.01.31
# 更新内容：多线程实现各结点并发安装组件
#           添加切换组件不同版本功能
#           重构代码
# 作    者：曲怀觞
# ***************************************************************************


import sys
import os
import re
# 需要安装 paramiko 模块 (ssh远程操作主机)
import paramiko
from getopt import getopt
from atexit import register
# 多线程并发
from threading import Thread
# 显示时间
from time import ctime
# 计算时间差
from datetime import datetime


# ###########################################################################
# function: load_config
# input:    config file(配置文件)
# return:   dict(配置信息存储在字典中)
# ###########################################################################
def load_config(cfg):
    '''
        读取hadoop安装配置文件，并生成配置信息字典
        input: hadoop_install.cfg
        return: dict_conf
    '''
    d = {}
    fh = open(cfg, 'r')

    for line in fh:
        if re.search('^#', line):
            next
        elif re.match('^$', line):
            next
        else:
            try:
                ( key, value ) = line.strip('\n').split(':')
                d[key] = value
            except:
                sys.exit("get key:" + key + " value:" + value + " error")

    return d


# ###########################################################################
# function: print_help
# input:    none
# return:   none
# ###########################################################################
def print_help():
    '''
        输出帮助信息
    '''
    print "# -------------------------------------------------"
    print "# Usage: hadoop_install.py -[cih] | -[adu] software"
    print "# -------------------------------------------------"
    print "# 卸载hadoop: -c or --clean"
    print "# 安装hadoop: -i or --install"
    print "# 帮助: -h or --help"
    print "# 添加组件: -a or --add software"
    print "# 删除组件: -d or --delete software"
    print "# 更新组件: -s or --switch software"
    print "# -------------------------------------------------"
    print "# 配置文件： hadoop_install.cfg"
    print "# -------------------------------------------------"


# ###########################################################################
# function: get_linkname
# input:    (d, software)
# return:   linkname
# ###########################################################################
def get_linkname(d, software):
    '''
        返回linkname
    '''
    if re.match('jdk', software):
        key = 'JAVA_HOME'
    else:
        key = re.search('(\w+)(_\S+)?-\d+\.\d+\.\d+', 
                software).group(1).upper() + '_HOME'

    return d[key]


# ###########################################################################
# function: scp_software
# input:    (d, software, host)
# return:   none
# ###########################################################################
def scp_software(d, software, host):
    '''
        根据压缩文件类型
        自动返回解压缩安装指令
    '''
    if host == d['nn_host']:
        pass
    else:
        scp_cmd = 'scp ' + d['SOFTWARE_PATH']       \
                    + software + ' ' + host + ':'   \
                    + d['INSTALL_PATH']

        try:
            os.system(scp_cmd)
            print 'scp ' + software + ' to ' + host + ' done!'
        except:
            sys.exit('scp ' + software + ' to ' + host + ' error')



# ###########################################################################
# function: uncompress_software
# input:    (d, software, host)
# return:   uncompress_cmd
# ###########################################################################
def uncompress_software(d, software, host):
    '''
        根据压缩文件类型
        自动返回解压缩安装指令
    '''
    if re.search(r'.tar.gz|.tgz', software):
        opt = '-zxf'
    elif re.search(r'.bz2', software):
        opt = '-jxf'

    install_path = d['INSTALL_PATH']

    if host == d['nn_host']:
        sw_path = d['SOFTWARE_PATH']
        uncompress_cmd = 'tar ' + opt + ' ' + sw_path       \
                    + software + ' -C ' + install_path
    else:
        sw_path = d['INSTALL_PATH']
        uncompress_cmd = uncompress_cmd = 'tar ' + opt      \
                    + ' ' + sw_path + software + ' -C '     \
                    + install_path + ' && rm -rf '          \
                    + sw_path + software

    return uncompress_cmd


# ###########################################################################
# function: link_software
# input:    (d, software)
# return:   link_cmd
# ###########################################################################
def link_software(d, software):
    '''
        返回创建软件链接命令
        链接目录为 /usr/mylink/
    '''
    link_name = get_linkname(d, software)
    link_path = d['LINK_HOME']
    install_path = d['INSTALL_PATH']
    upkname = software.split(r'.t')[0]
    
    link_cmd = 'if [ ! -d ' + link_path + ' ];then mkdir -p '   \
        + link_path + ';fi && if [ -e ' + link_path + link_name \
        + ' ];then rm ' + link_path + link_name                 \
        + ';fi && ln -s ' + install_path + upkname + ' '        \
        + link_path + link_name

    return link_cmd


# ###########################################################################
# function: profiled_software
# input:    (d, software)
# return:   profiled_cmd
# ###########################################################################
def profiled_software(d, software):
    '''
        返回配置环境变量指令
        启动服务自动载入
    '''
    link_name = get_linkname(d, software)
    profile_path = d['PROFILED']
    link_path = d['LINK_HOME']
    path_home = link_name.upper() + r'_HOME'
    
    profiled_cmd = 'echo export ' + path_home + '=' + link_path \
                        + link_name + ' > ' + profile_path      \
                        + link_name + r'.sh && echo export PATH=$PATH:' \
                        + '\$' + path_home + '/bin' + '>>'      \
                        + profile_path + link_name + r'.sh'

    if os.path.exists(profile_path + link_name + r'.sh'):
        profiled_cmd = ''

    return profiled_cmd


# ###########################################################################
# function: source_profile
# input:    (d, software)
# return:   source_cmd
# ###########################################################################
def source_profile(d, software):
    '''
        加载环境变量
    '''
    link_name = get_linkname(d, software)
    profile_path = d['PROFILED']
    source_cmd = 'source ' + profile_path + link_name + r'.sh'

    return source_cmd

# ###########################################################################
# function: operate_dir
# input:    (d, opt)
# return:   commands
# ###########################################################################
def operate_dir(d, opt):
    '''
        opt ==> 'mkdir -p' 创建目录
        'rm -rf' 删除目录
        返回操作hadoop相关工作目录指令，包括:
        1.NN_DATA_DIR
        2.SNN_DATA_DIR
        3.DN_DATA_DIR
        4.YARN_LOG_DIR
        5.HADOOP_LOG_DIR
        6.HADOOP_MAPRED_LOG_DIR
        7.YARN_PID_DIR
        8.HADOOP_PID_DIR
        9.HADOOP_MAPRED_PID_DIR
    '''
    nn_data_dir_cmd = opt + ' ' + d['NN_DATA_DIR']
    snn_data_dir_cmd = opt + ' ' + d['SNN_DATA_DIR']
    dn_data_dir_cmd = opt + ' ' + d['DN_DATA_DIR']
    yarn_log_dir_cmd = opt + ' ' + d['YARN_LOG_DIR']
    hadoop_log_dir_cmd = opt + ' ' + d['HADOOP_LOG_DIR']
    hadoop_mapred_log_dir_cmd = opt + ' ' + d['HADOOP_MAPRED_LOG_DIR']
    yarn_pid_dir_cmd = opt + ' ' + d['YARN_PID_DIR']
    hadoop_pid_dir_cmd = opt + ' ' + d['HADOOP_PID_DIR']
    hadoop_mapred_pid_dir_cmd = opt + ' ' + d['HADOOP_MAPRED_PID_DIR']
    
    return (nn_data_dir_cmd,
            snn_data_dir_cmd,
            dn_data_dir_cmd,
            yarn_log_dir_cmd,
            hadoop_log_dir_cmd,
            hadoop_mapred_log_dir_cmd,
            yarn_pid_dir_cmd,
            hadoop_pid_dir_cmd,
            hadoop_mapred_pid_dir_cmd)


# ###########################################################################
# function: create_user
# input:    (d)
# return:   commands
# ###########################################################################
def create_user(d):
    '''
        返回hadoop创建组、用户的指令，包括:
        1.GROUP_HADOOP
        2.USER_YARN
        3.USER_HDFS
        4.USER_MAPRED
    '''
    group_hadoop_cmd = 'groupadd ' + d['GROUP_HADOOP']
    user_yarn_cmd = 'useradd -g ' + d['GROUP_HADOOP']   \
                        + ' ' + d['USER_YARN']
    user_hdfs_cmd = 'useradd -g ' + d['GROUP_HADOOP']   \
                        + ' ' + d['USER_HDFS']
    user_mapred_cmd = 'useradd -g ' + d['GROUP_HADOOP'] \
                        + ' ' + d['USER_MAPRED']
    
    return (group_hadoop_cmd,
            user_yarn_cmd,
            user_hdfs_cmd,
            user_mapred_cmd)



# ###########################################################################
# function: clean_user
# input:    (d)
# return:   commands
# ###########################################################################
def clean_user(d):
    '''
        返回hadoop删除组、用户的指令，包括:
        1.GROUP_HADOOP
        2.USER_YARN
        3.USER_HDFS
        4.USER_MAPRED
    '''
    user_yarn_cmd = 'userdel ' + d['USER_YARN']
    user_hdfs_cmd = 'userdel ' + d['USER_HDFS']
    user_mapred_cmd = 'userdel ' + d['USER_MAPRED']
    group_hadoop_cmd = 'groupdel ' + d['GROUP_HADOOP']
    
    return (user_yarn_cmd,
            user_hdfs_cmd,
            user_mapred_cmd,
            group_hadoop_cmd)



# ###########################################################################
# function: chmod_user
# input:    (d)
# return:   commands
# ###########################################################################
def chmod_user(d):
    '''
        返回目录授权用户指令，包括:
        USER GROUP
        1.NN_DATA_DIR ==> HDFS HADOOP
        2.SNN_DATA_DIR ==> HDFS HADOOP
        3.DN_DATA_DIR ==> HDFS HADOOP
        4.YARN_LOG_DIR ==> YARN HADOOP
        5.HADOOP_LOG_DIR ==> HDFS HADOOP
        6.HADOOP_MAPRED_LOG_DIR ==> MAPRED HADOOP
        7.YARN_PID_DIR ==> YARN HADOOP
        8.HADOOP_PID_DIR ==> HDFS HADOOP
        9.HADOOP_MAPRED_PID_DIR ==> MAPRED HADOOP
    '''
    nn_data_dir_cmd = 'chown ' + d['USER_HDFS'] + ':'       \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['NN_DATA_DIR']
    snn_data_dir_cmd = 'chown ' + d['USER_HDFS'] + ':'      \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['SNN_DATA_DIR']
    dn_data_dir_cmd = 'chown ' + d['USER_HDFS'] + ':'       \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['DN_DATA_DIR']
    yarn_log_dir_cmd = 'chown ' + d['USER_YARN'] + ':'      \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['YARN_LOG_DIR']
    hadoop_log_dir_cmd = 'chown ' + d['USER_HDFS'] + ':'    \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['HADOOP_LOG_DIR']
    hadoop_mapred_log_dir_cmd = 'chown ' \
                        + d['USER_MAPRED'] + ':'            \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['HADOOP_MAPRED_LOG_DIR']
    yarn_pid_dir_cmd = 'chown ' + d['USER_YARN'] + ':'      \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['YARN_PID_DIR']
    hadoop_pid_dir_cmd = 'chown ' + d['USER_HDFS'] + ':'    \
                        + d['GROUP_HADOOP'] + ' '           \
                        + d['HADOOP_PID_DIR']
    hadoop_mapred_pid_dir_cmd = 'chown ' + d['USER_MAPRED'] \
                        + ':' + d['GROUP_HADOOP'] + ' '     \
                        + d['HADOOP_MAPRED_PID_DIR']
    
    return (nn_data_dir_cmd,
            snn_data_dir_cmd,
            dn_data_dir_cmd,
            yarn_log_dir_cmd,
            hadoop_log_dir_cmd,
            hadoop_mapred_log_dir_cmd,
            yarn_pid_dir_cmd,
            hadoop_pid_dir_cmd,
            hadoop_mapred_pid_dir_cmd)


# ###########################################################################
# function: set_env
# input:    (d)
# return:   commands
# ###########################################################################
def set_env(d):
    '''
        返回添加env配置文件指令，包括:
        1.HADOOP_LOG_DIR ==> hadoop-env.sh
        2.JAVA_HOME ==> hadoop-env.sh
        3.YARN_LOG_DIR ==> yarn-env.sh
        4.HADOOP_MAPRED_LOG_DIR ==> mapred-env.sh
        5.HADOOP_PID_DIR ==> hadoop-env.sh
        6.YARN_PID_DIR ==> yarn-env.sh
        7.HADOOP_MAPRED_PID_DIR ==> mapred-env.sh
    '''
    hadoop_log_dir_cmd = 'echo export HADOOP_LOG_DIR='      \
                        + d['HADOOP_LOG_DIR']               \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/hadoop-env.sh'
    hadoop_java_home_cmd = 'echo export JAVA_HOME='         \
                        + d['LINK_HOME']                    \
                        + d['JAVA_HOME']                    \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/hadoop-env.sh'
    yarn_log_dir_cmd = 'echo export YARN_LOG_DIR='          \
                        + d['YARN_LOG_DIR']                 \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/yarn-env.sh'
    hadoop_mapred_log_dir_cmd = 'echo export HADOOP_MAPRED_LOG_DIR=' \
                        + d['HADOOP_MAPRED_LOG_DIR']        \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/mapred-env.sh'
    hadoop_pid_dir_cmd = 'echo export HADOOP_PID_DIR='      \
                        + d['HADOOP_PID_DIR']               \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/hadoop-env.sh'
    yarn_pid_dir_cmd = 'echo export YARN_PID_DIR='          \
                        + d['YARN_PID_DIR']                 \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/yarn-env.sh'
    hadoop_mapred_pid_dir_cmd = 'echo export HADOOP_MAPRED_PID_DIR=' \
                        + d['HADOOP_MAPRED_PID_DIR']        \
                        + ' >> /usr/mylink/hadoop/etc/hadoop/mapred-env.sh'
    
    return (hadoop_log_dir_cmd,
            hadoop_java_home_cmd,
            yarn_log_dir_cmd,
            hadoop_mapred_log_dir_cmd,
            hadoop_pid_dir_cmd,
            yarn_pid_dir_cmd,
            hadoop_mapred_pid_dir_cmd)


# ###########################################################################
# function: call_func
# input:    (command, d, host)
# return:   none
# ###########################################################################
def call_func(command, d, host):
    '''
        执行命令：封装本地和ssh远程调用
    '''
    if host == d['nn_host']:
        try:
            os.system(command)
        except:
            sys.exit(command + " error!")
        
    else:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, int(d['PORT']), d['USER'], d['PASSWD'])
        except:
            sys.exit('create sshclient error!')
        
        try:
            (stdin, stdout, stderr) = ssh.exec_command(command)
        except:
            sys.exit(stderr)
        
        try:
            ssh.close()
        except:
            sys.exit('close sshclient error!')


# ###########################################################################
# function: group_steps
# input:    (d, software, host)
# return:   none
# ###########################################################################
def group_steps(d, software, host):
    '''
        对某一组件安装步骤组合
    '''
    # 复制软件包
    scp_software(d, software, host)
    # 解压软件包
    call_func(uncompress_software(d, software, host), d, host)
    print software + ' uncompressed.'
    # 创建软链接
    call_func(link_software(d, software), d, host)
    print software + ' link created.'
    # 创建自启动环境变量
    call_func(profiled_software(d, software), d, host)
    print software + ' profile created.'
    # 加载环境变量
    #call_func(source_profile(d, software), d, host)


# ###########################################################################
# function: install_software
# input:    (d, software)
# return:   none
# ###########################################################################
def install_software(d, software):
    '''
        安装hadoop及组件
        遍历主从节点
        执行各步骤返回的指令
    '''
    print 'At ' + ctime() + ' install ' + software + ' begin'
    print '=' * 48
    starttime = datetime.now()
    threads = []

    for host in d['all_host'].split(','):

        # 并发处理
        t = Thread(target=group_steps,
                args=(d, software, host))
        threads.append(t)

    numbers = range(len(d['all_host'].split(',')))

    for i in numbers:
        threads[i].start()

    for i in numbers:
        threads[i].join()

    endtime = datetime.now()
    print '=' * 48
    print 'At ' + ctime() + ' install ' + software + ' done!'
    print 'Use time: %d' % (endtime - starttime).seconds
    print '-' * 48
    print ''


# ###########################################################################
# function: switch_software
# input:    (d, software, host)
# return:   none
# ###########################################################################
def switch_software(d, software):
    '''
        切换软件版本
    '''
    for host in d['all_host'].split(','):
        call_func(link_software(d, software), d, host)
        print 'For ' + host + ' switch link to ' + software



# ###########################################################################
# function: clean_software
# input:    (d, software)
# return:   none
# ###########################################################################
def clean_software(d, software):
    '''
        1.清理/opt目录下软件
        2.删除/usr/mylink下链接
        3.删除/etc/profile.d目录下配置文件
    '''
    link_name = get_linkname(d, software)
    unpack_name = software.split(r'.t')[0]
    print 'Clean ' + software + ' please waiting...'
    print '=' * 48
    for host in d['all_host'].split(','):
    
        call_func('rm -rf ' + d['INSTALL_PATH'] + unpack_name, d, host)
        call_func('rm -rf ' + d['LINK_HOME'] + link_name, d, host)
        call_func('rm -rf ' + d['PROFILED'] + link_name + r'.sh', d, host)

        print 'Clean ' + host + ' done!'

    print '-' * 48

# ###########################################################################
# function: init_hadoop
# input:    (d)
# return:   none
# ###########################################################################
def init_hadoop(d):
    '''
        创建hadoop集群所需目录、用户等
        遍历主从节点
        执行各步骤返回的指令
    '''
    for host in d['all_host'].split(','):
        print "Create user and dir for " + host
        print '-' * 48

        for command in operate_dir(d, 'mkdir -p'):
            call_func(command, d, host)

        for command in create_user(d):
            call_func(command, d, host)

        for command in chmod_user(d):
            call_func(command, d, host)

        for command in set_env(d):
            call_func(command, d, host)

        print ''


# ###########################################################################
# function: clean_hadoop
# input:    (d)
# return:   none
# ###########################################################################
def clean_hadoop(d):
    # 清理用户及目录
    for host in d['all_host'].split(','):
        print "clean users and dir for " + host
        print '-' * 48

        for command in operate_dir(d, 'rm -rf'):
            call_func(command, d, host)

        for command in clean_user(d):
            call_func(command, d, host)


# ###########################################################################
# function: main
# input:    none
# return:   none
# ###########################################################################
def main(argv = None):
    '''
        主函数
    '''
    # 设置参数选项
    opts, args = getopt(sys.argv[1:], "a:cd:his:",      \
                    [                                   \
                        "add=", "clean", "delete=",     \
                        "help", "install", "switch="    \
                    ])
    argnum = len(opts)

    if not ( argnum == 1 or argnum == 2 ):
        sys.exit("Usage: hadoop_install.py -[cih] | -[ads] software_name")
    
    # 默认配置文件与安装脚本在同一目录下
    dict_conf = load_config("hadoop_install.cfg")
    
    for op, package_name in opts:
        # 软件包名称不为空时：
        # 从添加、删除、更新组件中选取
        if not package_name == '':
            if op in ( "-a", "--add" ):
                install_software(dict_conf, package_name)
            elif op in ( "-d", "--delete" ):
                clean_software(dict_conf, package_name)
            elif op in ( "-s", "--switch" ):
                switch_software(dict_conf, package_name)
            # 选项不存在
            else:
                sys.exit("There is no other options")
        
        # 软件包名称为空时：
        # 从安装、卸载、帮助选项中选取
        else:
            if op in ( "-c", "--clean" ):
                # 批量删除软件
                for key in dict_conf.keys():
                    if re.search(r'_PKG' ,key):
                        package_name = dict_conf[key]
                        try:
                            clean_software(dict_conf, package_name)
                        except:
                            sys.exit("clean " + package_name + " error")
                # 清理用户和目录
                clean_hadoop(dict_conf)

            # 帮助
            elif op in ( "-h", "--help" ):
                print_help()
                sys.exit()
            # 批量安装
            elif op in ( "-i", "--install" ):
                for key in dict_conf.keys():
                    if re.search(r'_PKG' ,key):
                        package_name = dict_conf[key]
                        try:
                            install_software(dict_conf, package_name)
                        except:
                            sys.exit("install " + package_name + " error")
                
                init_hadoop(dict_conf)
            # 选项不存在
            else:
                sys.exit("There is no other options")


# ###########################################################################
# 程序入口
# ###########################################################################
if __name__ == "__main__":
    sys.exit(main())
