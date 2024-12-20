# yourapplication/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
import logging
from logging.handlers import RotatingFileHandler

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化数据库
    db.init_app(app)

    # 注册蓝图
    from yourapplication.views import main_bp
    app.register_blueprint(main_bp)

    # 配置日志
    configure_logging(app)

    # 创建数据和日志目录
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(app.config['LOG_DIR'], exist_ok=True)

    # 创建数据库表
    with app.app_context():
        db.create_all()
        app.logger.info("数据库表已创建")

    # 移除后台线程的启动
    # from yourapplication.utils import start_background_tasks
    # start_background_tasks(app)

    return app

def configure_logging(app):
    # 确保日志目录存在
    os.makedirs(app.config['LOG_DIR'], exist_ok=True)

    # 设置日志文件路径
    log_file_path = app.config['LOG_FILE']

    # 配置基于文件大小的轮转日志
    handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5)  # 5MB，保留5个备份
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
