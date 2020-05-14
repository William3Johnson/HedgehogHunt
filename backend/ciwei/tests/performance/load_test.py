# encoding: utf-8
"""
@author: github/100101001
@contact: 17702113437@163.com
@time: 2020/5/12 上午1:19
@file: load_test.py
@desc: 
"""
# 逐步增加负载，绘制性能曲线
from tests.performance.performance_test_base import RestfulApisCallerAsync


class LoadTestInitiator(RestfulApisCallerAsync):

    def __init__(self, client_load):
        super(LoadTestInitiator, self).__init__('load_test_{}.log'.format(client_load), 'load_call_{}.log'.format(client_load))

    @classmethod
    def runAll(cls, lower_bound=0, upper_bound=0, step=1):
        for i in range(lower_bound, upper_bound, step):
            runner = cls(i)
            runner.random_call()



if __name__ == '__main__':
    LoadTestInitiator.runAll(10, 1000, 300)

