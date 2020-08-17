# -*- coding:utf-8 -*-
"""
Dec: 自动升级某些Python第三方库
Created on: 2018.07.17
Author: Iflier
Modified on: 2018.07.18
1.添加对 pip 版本的检查
2.对 pip 命令添加的输出添加columns控制
3.对于需要突出显示的部分，彩色化输出
Modified on: 2018.07.19
把升级的包记录到日志
Modified on: 2018.08.31
执行自动升级命令前，检查当前的网络是否可用
Modified on: 2018.10.05
添加升级pip工具自身的命令
Modified on: 2020.08.17
新加排除自动升级的包
"""
import sys
import logging
import subprocess
from typing import TypeVar, List, Tuple
from subprocess import TimeoutExpired

from colorama import init, Fore, Back, Style


init(autoreset=True)
print("[INFO] System encoding format: {0}".format(sys.getdefaultencoding()))
# 由于部分包库存在兼容性问题，暂时不便升级的库
notUpgradeLibs = ['amqp', 'beautifulsoup4', 'babel', 'grpcio', 'botocore',
                  'html5lib', 'boto3', 'gevent', 'mxnet', 'opencv-python',
                  'pypiwin32', 'python-dateutil', 'pytz', 'regex', 'keras',
                  'tensorflow', 'tensorboard', 'tqdm', 'yarl', 'kombu',
                  'bleach', 'async-timeout', 'setuptools', 'protobuf',
                  'pyqt5', 'numpy', 'spyder-kernels', 'prompt-toolkit',
                  'h11', 'isort', 'msgpack', 'protobuf', 'startlette'
                  ]
prepareUpgradeLibs = list()
prepareUpgradeLibsInfo = list()
logging.basicConfig(filename="upgrade.log", filemode='a',
                    datefmt="%c", level=logging.DEBUG,
                    format="%(levelname)s %(asctime)s %(message)s")
logger = logging.getLogger()


def runCommand(command: str, timeout: int = 150) -> TypeVar("commandResultType", List[bytes], None):
    """
    1.命令执行超时，返回None
    2.执行成功时，返回按行的未被解码的控制台输出
    3.不对命令输出做解码操作
    """
    # 检查传入的命令是否为字符串
    assert isinstance(command, str), "Check your command type!"
    print("Running command: {0} ...".format(command))
    try:
        commandResult = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        _ = commandResult.wait(timeout=timeout)
        return commandResult.stdout.readlines()
    except TimeoutExpired as err:
        print("[ERROR] {0}, Prepare to exit ...".format(err))
        logger.error("Bad network environment.")
        return None

# 自动升级包之前，检查当前网络环境
pingCommandResultLines = runCommand("ping -n 10 www.baidu.com")
if pingCommandResultLines is None:
    sys.exit(0)
elif len(pingCommandResultLines) == 1:
    print("[ERROR] Failed to connect to network :-(, prepare to exit ...")
    logger.error("Failed to connect to network.")
    sys.exit(0)
else:
    # 解析命令行输出。Windows命令行输出为GBK编码的字节
    statisticResult = pingCommandResultLines[-3].decode("GBK").split('，')[-2]  # 这个是汉字符号的逗号
    print("Statistic result: {0}".format(statisticResult))
    packetLossRate = statisticResult.split()[2]
    print("PacketLoss Rate = {0} %".format(packetLossRate))
    if int(packetLossRate) >= 50:
        # 丢包率大于 50% 的情况下，退出升级
        print("Current network environment may not good, prepareing to exit ...")
        logger.info("Current network environment is bad.")
        sys.exit(0)

# 检查pip工具的版本号是否大于等于10.x
pipToolVersionCheckResult = runCommand("pip --version")
pipVersion = pipToolVersionCheckResult[0].decode(encoding='utf-8').split()[1]

# 针对不同的 pip 版本,应用不同的输出
if pipVersion.startswith("1"):
    logger.info("Running command for checking packages to be upgrade.")
    pipListCommandResultLines = runCommand("pip list -o --format columns", timeout=300)
    if pipListCommandResultLines is None:
        sys.exit(0)
    for line in pipListCommandResultLines:
        packagesInfo = line.decode()
        if 'wheel' in packagesInfo and packagesInfo.split()[0].lower() not in notUpgradeLibs:
            prepareUpgradeLibsInfo.append(packagesInfo)
            prepareUpgradeLibs.append(packagesInfo.split()[0])
    # print(complPro.stderr.decode())
    # 针对有需要升级的包的情况
    if len(prepareUpgradeLibs) != 0:
        logger.info("Begin to upgrade packages.")
        print("There are {0:^5,d} packages need to upgrade, they are:\n {1}".format(len(prepareUpgradeLibs), prepareUpgradeLibs))
        print(Fore.RED + Back.BLUE + "Upgrading packages ..." + Style.RESET_ALL)
        # 如果检查到pip工具自身需要升级，先升级自己
        if "pip" in prepareUpgradeLibs:
            if sys.platform.startswith("win32"):
                pipInstallCommandResult = runCommand("python -m pip install --upgrade pip")
                if pipInstallCommandResult is None:
                    print("During upgrade package: {0}, occurred an error :-(".format("pip"))
                    logger.error("When upgrade {0}, an error occurred.".format("pip"))
                else:
                    print("Succeed upgrade package: {0}, from {1} to {2}.".format("pip", prepareUpgradeLibsInfo[prepareUpgradeLibs.index("pip")].split()[1], prepareUpgradeLibsInfo[prepareUpgradeLibs.index("pip")].split()[2]))
                    logger.info("Upgrade package {0} from {1} to {2} succeed.".format("pip", prepareUpgradeLibsInfo[prepareUpgradeLibs.index("pip")].split()[1], prepareUpgradeLibsInfo[prepareUpgradeLibs.index("pip")].split()[2]))
            # 从两个列表中删除自身的信息，这样不会影响后面其他包的升级
            # 可能是其他的OS，因为升级使用命令可能不一样，还是把pip及其升级信息从列表中删除比较稳定。比如Ubuntu 系统可能使用的是pip3工具升级各种包
            prepareUpgradeLibsInfo.remove(prepareUpgradeLibsInfo[prepareUpgradeLibs.index("pip")])
            prepareUpgradeLibs.remove("pip")  # 这个是对列表自身的修改，返回None
        for package, packageInfo in zip(prepareUpgradeLibs, prepareUpgradeLibsInfo):
            pipInstallCommandResult = runCommand("pip install -U {0}".format(package), timeout=155)
            if pipInstallCommandResult is None:
                print("During upgrade package: {0}, occurred an error :-(".format(package))
                logger.error("When upgrade {0}, an error occurred.".format(package))
            else:
                print("Succeed upgrade package: {0}, from {1} to {2}.".format(package, packageInfo.split()[1], packageInfo.split()[2]))
                logger.info("Upgrade package {0} from {1} to {2} succeed.".format(package, packageInfo.split()[1], packageInfo.split()[2]))
        logger.info("Upgrade finished.")
    else:
        print("Congratuations! All the libraries are the newest!")
else:
    print(Fore.RED + Back.YELLOW + "Upgrade your pip version, please." + Style.RESET_ALL)
    logger.info("Encount an old pip version :-(")

# 检查已安装的包库的兼容性
print(Fore.BLACK + Back.BLUE + "Prepare to verify installed packages have compatible dependencies ..." + Style.RESET_ALL)
pipCheckCommandResultLines = runCommand("pip check")
if len(pipCheckCommandResultLines) != 0:
    print(Fore.RED + Back.WHITE + "Warning(s):" + Style.RESET_ALL)
    for line in pipCheckCommandResultLines:
        print(line.decode(encoding='utf-8'))
else:
    print("Congratuations! All the libraries are compatied with each other.!")
logger.info("Done.")
print(Fore.BLUE + Back.BLACK + "Done." + Style.RESET_ALL)
