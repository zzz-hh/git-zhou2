# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :test.py
# @Time      :2025/5/6 下午4:25
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com

import json
import yaml

file = r"./config/components.json"
with open(file, "r", encoding="utf-8") as f:
    res = json.load(f)
    print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    # print(res)
    # print(type(res))
