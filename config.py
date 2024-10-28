# config.py

import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 日志配置
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')

    # 请求头配置
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "http://cgyytyb.cpu.edu.cn/wap/yuyue"
    }

    # 场馆选项
    CHANGGUAN_OPTIONS = {
        1: "田径场健身房",
        2: "体育馆三楼羽毛球馆1号场",
        3: "体育馆三楼羽毛球馆2号场",
        4: "体育馆三楼羽毛球馆3号场",
        5: "体育馆三楼羽毛球馆4号场",
        6: "体育馆三楼羽毛球馆5号场",
        7: "体育馆三楼羽毛球馆6号场",
        8: "体育馆三楼羽毛球馆7号场",
        9: "体育馆一楼羽毛球馆1号场",
        10: "体育馆一楼羽毛球馆2号场",
        11: "体育馆一楼羽毛球馆3号场",
        12: "体育馆一楼羽毛球馆4号场",
        13: "体育馆一楼羽毛球馆5号场",
        14: "体育馆一楼羽毛球馆6号场",
        15: "体育馆一楼教室一",
        16: "体育馆一楼教室二",
        17: "体育馆一楼教室三",
        18: "体育馆四楼教室四",
        22: "体育场形体房",
        23: "体育场跆拳道房",
    }

    # 姓名和 openid 映射
    NAME_OPENID_MAP = {
        "高利明": "odBu7wrvL6I4doCdkFcqm6j0Ng8E",
        "汪子颖": "odBu7wrUQy59WPniRKKsUJZ-Y5ug",
        "刘紫涵": "odBu7wtPIbU7FxS6XSBTEY2HsoJ0"
    }

    DEFAULT_OPENID = "odBu7wrvL6I4doCdkFcqm6j0Ng8Enanyecpu123@#$gaoliming123CPU@"
