# yourapplication/utils.py

import asyncio
import aiohttp
import time
import logging
from bs4 import BeautifulSoup
from threading import Thread
from flask import current_app
from yourapplication.models import db, Order
from sqlalchemy.exc import SQLAlchemyError

# 启动后台更新任务
def start_background_tasks(app):
    # 启动一个线程不断运行更新任务
    def run_update():
        with app.app_context():
            while True:
                try:
                    update_database(app)  # 调用更新数据库的函数
                except Exception as e:
                    app.logger.error(f"后台更新任务出错：{e}")  # 记录错误日志
                time.sleep(180)  # 每隔3分钟运行一次

    thread = Thread(target=run_update)
    thread.daemon = True
    thread.start()  # 启动后台线程

# 更新数据库的函数
def update_database(app):
    app.logger.info("开始更新数据库")
    # 获取数据库中最大的 yuyue_id，如果不存在则设为 823
    max_yuyue_id = db.session.query(db.func.max(Order.yuyue_id)).scalar() or 823
    # 使用异步获取新的订单数据，范围为 max_yuyue_id + 1 到 max_yuyue_id + 2000
    new_orders = asyncio.run(fetch_new_orders(app, max_yuyue_id + 1, max_yuyue_id + 500))

    for order_data in new_orders:
        if order_data:
            # 检查数据库中是否已经存在相同的 yuyue_id
            existing_order = Order.query.filter_by(yuyue_id=order_data['yuyue_id']).first()
            if not existing_order:
                # 如果订单不存在，创建新的 Order 对象并添加到数据库
                order = Order(
                    yuyue_id=order_data['yuyue_id'],
                    venue=order_data['venue'],
                    name=order_data['name'],
                    phone=order_data['phone'],
                    date=order_data['date'],
                    time=order_data['time']
                )
                try:
                    db.session.add(order)
                    db.session.commit()  # 提交新订单到数据库
                    app.logger.info(f"添加新订单 {order_data['yuyue_id']}")
                except SQLAlchemyError as e:
                    db.session.rollback()  # 出现错误时回滚
                    app.logger.error(f"数据库错误：{e}")
    app.logger.info("数据库更新完成")

# 异步获取新订单数据
async def fetch_new_orders(app, start_id, end_id):
    tasks = []
    async with aiohttp.ClientSession() as session:
        # 创建获取每个订单的任务列表
        for yuyue_id in range(start_id, end_id):
            tasks.append(fetch_order(app, session, yuyue_id))
        results = await asyncio.gather(*tasks)  # 并发执行所有任务
    return results

# 异步获取单个订单的函数
async def fetch_order(app, session, yuyue_id):
    url = f"http://cgyytyb.cpu.edu.cn/wap/yuyueIn?id={yuyue_id}"
    headers = app.config['HEADERS']  # 从配置中获取请求头
    try:
        # 发起 GET 请求获取订单内容
        async with session.get(url, headers=headers) as response:
            content = await response.text()
            order_data = extract_order_info(app, yuyue_id, content)  # 提取订单信息
            await asyncio.sleep(0.1)  # 控制请求频率，防止请求过多
            return order_data
    except Exception as e:
        app.logger.error(f"获取订单 {yuyue_id} 时出错：{e}")
        return None

# 提取订单信息的函数
def extract_order_info(app, yuyue_id, content):
    soup = BeautifulSoup(content, 'html.parser')
    order_data = {}
    try:
        if '审核通过，可以进场' in content:
            # 找到预约场馆
            venue_label = soup.find('label', string='预约场馆')
            if not venue_label:
                app.logger.error(f"无法找到预约场馆标签，yuyue_id={yuyue_id}")
                return None
            venue = venue_label.find_next_sibling('div').text.strip()

            # 找到预约姓名和电话
            name_hp_div = soup.find('label', string='预约姓名').find_next_sibling('div')
            if not name_hp_div:
                app.logger.error(f"无法找到预约姓名标签，yuyue_id={yuyue_id}")
                return None
            name = name_hp_div.contents[0].strip()
            phone = name_hp_div.find('span').text.strip() if name_hp_div.find('span') else ''

            # 找到预约时间
            date_time_div = soup.find('label', string='预约时间').parent
            date_span = date_time_div.find('span', style='font-weight:600;margin-right:1rem')
            date = date_span.text.strip() if date_span else ''

            time_em = date_time_div.find('em')
            time_info = time_em.text.strip() if time_em else ''

            # 组装订单信息字典
            order_data = {
                'yuyue_id': yuyue_id,
                'venue': venue,
                'name': name,
                'phone': phone,
                'date': date,
                'time': time_info
            }
            app.logger.info(f"提取订单 {yuyue_id} 成功")
        else:
            # 订单未审核通过或其他状态
            app.logger.info(f"订单 {yuyue_id} 状态不符")
            return None
    except Exception as e:
        app.logger.error(f"提取订单 {yuyue_id} 时出错：{e}")
        return None

    return order_data
